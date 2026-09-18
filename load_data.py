"""
load raw data from taipei-attractions.json and save to database
"""

import json
import re

import mysql.connector
from mysql.connector import Error

try:
    db = mysql.connector.connect(
            host='localhost',
            user='admin',
            password='Password1234!'
        )
except Error as e:
    print(f"database connection error:{e}")

# load raw data form json file
def load_json():
    with open("./data/taipei-attractions.json", encoding="utf-8") as file:
        content = json.load(file)
    return content

# process raw data
def process_data(content: dict):
    attractionList = content["list"]
    return attractionList


def get_integer_column_type(cursor, table_name: str) -> str:
    cursor.execute(
        "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
        "AND COLUMN_NAME = 'id'",
        (table_name,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"找不到 {table_name}.id 欄位")

    column_type = str(row[0]).strip().lower()
    match = re.fullmatch(
        r"(tinyint|smallint|mediumint|int|bigint)(?:\(\d+\))?( unsigned)?",
        column_type,
    )
    if match is None:
        raise ValueError(f"{table_name}.id 不是支援的整數型別: {column_type}")

    integer_type = match.group(1).upper()
    if match.group(2):
        integer_type += " UNSIGNED"
    return integer_type

# create database and tables
def create_database():
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS attractionDB")
        cursor.execute("USE attractionDB")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attractions (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                address TEXT NOT NULL,
                transport TEXT NOT NULL,
                mrt TEXT,
                lat DECIMAL(8,6) NOT NULL,
                lng DECIMAL(9,6) NOT NULL,
                images TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                api_token CHAR(64) NULL UNIQUE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
                )
        cursor.execute(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
            "AND COLUMN_NAME = 'api_token'"
        )
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN api_token CHAR(64) NULL UNIQUE")
        user_id_type = get_integer_column_type(cursor, "users")
        attraction_id_type = get_integer_column_type(cursor, "attractions")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS booking (
                id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                date DATE NOT NULL,
                user_id {user_id_type} NOT NULL,
                time ENUM('morning', 'afternoon') NOT NULL,
                price INT UNSIGNED NOT NULL,
                attraction_id {attraction_id_type} NOT NULL,
                UNIQUE KEY unique_booking_user (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (attraction_id) REFERENCES attractions(id)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS orders (
                id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                number VARCHAR(50) NOT NULL UNIQUE,
                user_id {user_id_type} NOT NULL,
                attraction_id {attraction_id_type} NOT NULL,
                date DATE NOT NULL,
                time ENUM('morning', 'afternoon') NOT NULL,
                price INT UNSIGNED NOT NULL,
                contact_name VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL,
                contact_phone VARCHAR(30) NOT NULL,
                status ENUM('UNPAID', 'PAID') NOT NULL DEFAULT 'UNPAID',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (attraction_id) REFERENCES attractions(id)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
    except (Error, ValueError) as e:
        print(f"database creation error: {e}")
    finally:
        if cursor is not None:
            cursor.close()

def save_attr_to_db(attrList):
    cursor = None
    try:
        cursor = db.cursor()
        for attr in attrList:
            name, category, description = attr['name'], attr['CAT'], attr['description']
            address, transport, mrt = attr['address'], attr['direction'], attr['MRT']
            lat, lng, images = attr['latitude'], attr['longitude'], attr['imgurls']
            cursor.execute("INSERT INTO attractions (name, category, description, address, transport, mrt, lat, lng, images) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);", 
                           (name, category, description, address, transport, mrt, lat, lng, images)
                           )
        db.commit()
    except Error as e:
        db.rollback()
        print(f"data insertion error:{e}")
    finally:
        if cursor is not None:
            cursor.close()

if __name__ == "__main__":
    create_database()
    content = load_json()
    attrList = process_data(content)
    save_attr_to_db(attrList)
