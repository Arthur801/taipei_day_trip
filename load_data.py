"""
load raw data from taipei-attractions.json and save to database
"""

import json

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
    with open("./data/taipei-attractions.json") as file:
        content = json.load(file)
    return content

# process raw data
def process_data(content: dict):
    attractionList = content["list"]
    return attractionList

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
                lat DECIMAL NOT NULL,
                lng DECIMAL NOT NULL,
                images TEXT NOT NULL
            );
            """
        )
    except Error as e:
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