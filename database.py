import sqlite3
import uuid

def create_chat_history_table():
    try:
        chat_history_conn = sqlite3.connect("chat_history.db")
        chat_history_cur = chat_history_conn.cursor()
        chat_history_cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history 
            (
                id BLOB PRIMARY KEY,              
                role TEXT,
                chat TEXT
            )
        """)
        return chat_history_conn
    except sqlite3.Error as error:
        print("Error creating chat_history table:", error)


def store_chat_history(user,assistant):
    
    try:
        conn = create_chat_history_table()
        cur = conn.cursor()
        datas=[user,assistant]
        for data in datas: 
            id_uuid = str(uuid.uuid4())
            cur.execute(f"""
                INSERT INTO chat_history VALUES (
                        '{id_uuid}',
                        '{data['role']}', 
                        '{data['content']}'     
                    )
            """
            )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as error:
        print("Error storing chat history log:", error)
    except Exception as e:
        print(f"Error: {e}")