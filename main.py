import logging
import os
import random
import time
from argparse import ArgumentParser, RawTextHelpFormatter
import psycopg2
from psycopg2.errors import SerializationFailure
import psycopg2.extras


def create_accounts(conn):
    id_acc = input("Enter the Account ID : ")
    full_name = input("Enter the full name: ")
    city = input("Enter the City : ")
    balance = input("Enter the balance : ")

    with conn.cursor() as cur:
        cur.execute("INSERT INTO bank values(%s,%s,%s,%s,'true')", (id_acc, full_name, city, balance))

    conn.commit()
    print("account created.")


def delete_account(remove_ID, conn):
    with conn.cursor() as cur:
        rd = str(remove_ID)
        cur.execute(f"DELETE FROM bank WHERE id_acc={rd}")
        print("Done")
        logging.debug("delete_account(): status message: %s",
                      cur.statusmessage)
    conn.commit()


def print_balances(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id_acc, balance FROM bank")
        logging.debug("print_balances(): status message: %s",
                      cur.statusmessage)
        rows = cur.fetchall()
        conn.commit()
        print(f"Balances at {time.asctime()}:")
        for row in rows:
            print("account id: {0}  balance: ${1:2d}".format(row['id_acc'], row['balance']))


def show_accounts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM bank")
        logging.debug("print_balances(): status message: %s",
                      cur.statusmessage)
        rows = cur.fetchall()
        conn.commit()
        print(rows)
        print(f"Balances at {time.asctime()}:")
        print("_" * 100)

        for row in rows:
            print("account id: {0} | full Name:{1} | city: {2} | balance: ${3:2d} | status: {4}".format(row['id_acc'],
                                                                                                        row[
                                                                                                            'full_name'],
                                                                                                        row['city'],
                                                                                                        row['balance'],
                                                                                                        row['status']))
            print("_" * 100)


def transfer_funds(conn, frm, to, amount):
    with conn.cursor() as cur:
        cur.execute("SELECT balance FROM bank WHERE id_acc = %s", (frm,))
        from_balance = cur.fetchone()['balance']
        while from_balance < amount:
            amount = int(input("The balance < amount ,try again : "))

        cur.execute(
            "UPDATE bank SET balance = balance - %s WHERE id_acc = %s", (
                amount, frm)
        )
        cur.execute(
            "UPDATE bank SET balance = balance + %s WHERE id_acc = %s", (
                amount, to)
        )

    conn.commit()
    logging.debug("transfer_funds(): status message: %s", cur.statusmessage)


def run_transaction(conn, op, max_retries=3):
    """
    Execute the operation *op(conn)* retrying serialization failure.

    If the database returns an error asking to retry the transaction, retry it
    *max_retries* times before giving up (and propagate it).
    """
    # leaving this block the transaction will commit or rollback
    # (if leaving with an exception)
    with conn:
        for retry in range(1, max_retries + 1):
            try:
                op(conn)

                # If we reach this point, we were able to commit, so we break
                # from the retry loop.
                return

            except SerializationFailure as e:
                # This is a retry error, so we roll back the current
                # transaction and sleep for a bit before retrying. The
                # sleep time increases for each failed transaction.
                logging.debug("got error: %s", e)
                conn.rollback()
                logging.debug("EXECUTE SERIALIZATION_FAILURE BRANCH")
                sleep_ms = (2 ** retry) * 0.1 * (random.random() + 0.5)
                logging.debug("Sleeping %s seconds", sleep_ms)
                time.sleep(sleep_ms)

            except psycopg2.Error as e:
                logging.debug("got error: %s", e)
                logging.debug("EXECUTE NON-SERIALIZATION_FAILURE BRANCH")
                raise e

        raise ValueError(
            f"transaction did not succeed after {max_retries} retries")


def main():
    URL = "YOUR_DATABASE_URL"

    if URL == "YOUR_DATABASE_URL":
        print("Please set the DATABASE_URL first.\nmain() -> URL")
        return "Exiting..."

    try:
        conn = psycopg2.connect(URL,
                                application_name="$imple Bank System",
                                cursor_factory=psycopg2.extras.RealDictCursor)

    except Exception as e:
        print(f"database connection failed -> \n{e}")
        return
        
    while True:
        inp = input("""
        1. Transfer money
        2. delete account
        3. Create account
        4. Show accounts
        0. Exit
        >>> """)

        if inp == '1':
            amount = int(input("amount > "))
            toId = int(input("to ID > "))
            fromId = int(input("From ID > "))

            try:
                run_transaction(conn, lambda conn: transfer_funds(conn, fromId, toId, amount))

            except ValueError as ve:
                # Below, we print the error and continue on so this example is easy to
                # run (and run, and run...).  In real code you should handle this error
                # and any others thrown by the database interaction.
                logging.debug("run_transaction(conn, op) failed: %s", ve)
            print_balances(conn)

        elif inp == '2':
            rm_ID = int(input("Enter the Account ID :"))
            delete_account(rm_ID, conn)

        elif inp == '3':
            create_accounts(conn)
        elif inp == '4':
            show_accounts(conn)
        elif inp == '0':
            break
        else:
            pass

    conn.close()


if __name__ == "__main__":
    main()
