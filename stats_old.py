import sqlite3
import pandas as pd
from transformers import pipeline
from deep_translator import GoogleTranslator

def display_all_data(db_name):
    print(f"\n--- Contents of {db_name} ---")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Get names of all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table_name in tables:
        name = table_name[0]
        print(f"\nTable: {name}")
        # Use Pandas for a clean, readable table format
        df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
        print(df.to_string(index=False))
        
    conn.close()


def get_stats(user_id):
    """Calculates performance metrics for a specific user."""

    # Connect to tasks.db database
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()

    # Link users.db to the current connection
    cursor.execute("ATTACH DATABASE 'users.db' AS u_db")

    query = """
    SELECT 
        t.task_is_completed, 
        t.task_priority,
        t.task_category
    FROM tasks t
    WHERE t.user_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    if df.empty:
        return [0, 0, 0, "N/A", "N/A"]

    ## Calculate metrics
    total = len(df)
    completed_df = df[df['task_is_completed'] == 1]
    completed_count = len(completed_df)
    
    # 1. Completion Rate
    completion_rate = round((completed_count / total) * 100, 1)
    
    # 2. Volume
    volume = total
    
    # 3. Focus Score (Priority)
    focus_score = round(completed_df['task_priority'].mean(), 1) if completed_count > 0 else 0

    # 4. Most Frequent Category (What they plan most)
    most_frequent_cat = df['task_category'].mode()[0] if not df['task_category'].empty else "None"

    # 5. Best Category (What they finish most)
    best_category = completed_df['task_category'].mode()[0] if not completed_df.empty else "None"

    # Testing print
    # print(f"Stats Calculated: Rate: {completion_rate}, Vol: {volume}, Focus: {focus_score}, Freq: {most_frequent_cat}, Best: {best_category}")

    return [completion_rate, volume, focus_score, most_frequent_cat, best_category]

def get_comment(stats_list):
    """Generates a professional productivity comment based on stats."""
    if not stats_list or stats_list[0] == 0:
        return "No activity recorded yet. Start completing tasks to see your evaluation!"

    # Initialize lightweight model
    evaluator = pipeline("text2text-generation", model="google/flan-t5-small")

    prompt = (
        f"Context: A user has a task completion rate of {stats_list[0]}%, "
        f"has managed {stats_list[1]} total tasks, and has a priority focus of {stats_list[2]}. "
        "Task: Write a one-sentence professional feedback for this user's profile."
    )
    
    result = evaluator(prompt, max_length=50, do_sample=False)
    comment = GoogleTranslator(source='auto', target='tr').translate(result[0]['generated_text'])
    return comment

## Example Usage ##
# Display databases
# display_all_data("tasks.db")
# display_all_data("users.db")

# Test functions
stats = get_stats(1)
comment = get_comment(stats)
print(f"Stats: {stats}")
print(f"AI Comment: {comment}")
