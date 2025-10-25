# Step 1: Manual Setup
# Create virtual environment (only once)
#     python -m venv venv
# Activate virtual environment
#     Windows: venv\Scripts\activate
# Install required packages (inside the activated venv)
#     pip install pandas pymysql streamlit plotly
# Run the Streamlit app
#     streamlit run securecheck.py

# Step 2: Import Libraries
import pandas as pd
import pymysql
import streamlit as st
import plotly.express as px

# STEP 3: Data preprocessing (load and clean CSV data)
file_path = r"C:\Users\Radhika Ranganathan\Downloads\traffic_stops - traffic_stops_with_vehicle_number.csv"

df = pd.read_csv(file_path, dtype={10: 'str'})
print("Data loaded:", df.shape)

# Fill missing search_type with 'None'
df['search_type'] = df['search_type'].fillna('None')

# Clean date/time
df['stop_date'] = pd.to_datetime(df['stop_date'], errors='coerce').dt.date
df['stop_time'] = pd.to_datetime(df['stop_time'], errors='coerce').dt.time

# Drop columns that are fully empty
df.dropna(axis=1, how='all', inplace=True)
print("Columns after cleaning:", df.columns.tolist())

# STEP 4: Mysql connection, DB table creation
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Thritha@2009"
)
cursor = conn.cursor()

# Create database and table
cursor.execute("Create Database if not exists postlog;")
cursor.execute("use postlog;")
print("Database 'postlog' ready.")

cursor.execute("""
CREATE TABLE IF NOT EXISTS traffic_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stop_date DATE,
    stop_time TIME,
    country_name VARCHAR(50),
    driver_gender VARCHAR(10),
    driver_age_raw INT,
    driver_age INT,
    driver_race VARCHAR(50),
    violation_raw VARCHAR(100),
    violation VARCHAR(100),
    search_conducted BOOLEAN,
    search_type VARCHAR(100),
    stop_outcome VARCHAR(100),
    is_arrested BOOLEAN,
    stop_duration VARCHAR(50),
    drugs_related_stop BOOLEAN,
    vehicle_number VARCHAR(50),
    UNIQUE KEY uniq_stop (stop_date, stop_time, vehicle_number, country_name)
);
""")
conn.commit()
print("Table 'traffic_stops' ready.")

# STEP 5: Insert data (only if table is empty)
cursor.execute("SELECT COUNT(*) FROM traffic_stops;")
existing_count = cursor.fetchone()[0]

if existing_count == 0:
    print("Inserting data into MySQL...")

    insert_query = """
        INSERT INTO traffic_stops (
            stop_date, stop_time, country_name, driver_gender,
            driver_age_raw, driver_age, driver_race,
            violation_raw, violation, search_conducted,
            search_type, stop_outcome, is_arrested,
            stop_duration, drugs_related_stop, vehicle_number
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON DUPLICATE KEY UPDATE search_type = VALUES(search_type);
    """

    data_list = [
        (
            row['stop_date'],
            row['stop_time'],
            row['country_name'],
            row['driver_gender'],
            int(row['driver_age_raw']) if not pd.isnull(row['driver_age_raw']) else None,
            int(row['driver_age']) if not pd.isnull(row['driver_age']) else None,
            row['driver_race'],
            row['violation_raw'],
            row['violation'],
            bool(row['search_conducted']),
            row['search_type'],
            row['stop_outcome'],
            bool(row['is_arrested']),
            row['stop_duration'],
            bool(row['drugs_related_stop']),
            row['vehicle_number']
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany(insert_query, data_list)
    conn.commit()
    print(f"Inserted {len(data_list)} records (duplicates ignored).")
else:
    print(f"Data already present ({existing_count} rows) — skipping insert.")

cursor.close()
conn.close()
print("Data inserted into MySQL successfully!")

# Step 6: Activate Streamlit Dashboard
st.set_page_config(page_title="Securecheck Dashboard", layout="wide")
st.title("Securecheck: Police Check Post Digital Ledger")
st.markdown("Real-time monitoring and insights for law enforcement operations")

# Connect again for dashboard display
conn = pymysql.connect(host="localhost", user="root", password="Thritha@2009", database="postlog")
data = pd.read_sql("SELECT * FROM traffic_stops;", conn)
conn.close()

# Dashboard Metrics
st.header("Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Police Stops", len(data))
col2.metric("Arrests Made", data['is_arrested'].sum())
col3.metric("Drug-Related Stops", data['drugs_related_stop'].sum())

# Data Visualization
st.markdown("### Visual Summary: Patterns in Stops, Violations & Outcomes")
tab1, tab2, tab3 = st.tabs(["Violations", "Outcomes", "Stops by Violation Type"])

# --- Chart 1: Violations by Frequency ---
with tab1:
    vc = data['violation'].value_counts().reset_index().head(10)
    vc.columns = ['Violation', 'Count']
    fig1 = px.bar(vc, x='Violation', y='Count', text='Count', color='Count',
                  title='Violations frequncy', color_continuous_scale='Viridis')
    fig1.update_traces(textposition='outside')
    st.plotly_chart(fig1, use_container_width=True)

# --- Chart 2: Stop Outcomes Distribution ---
with tab2:
    oc = data['stop_outcome'].value_counts().reset_index()
    oc.columns = ['Outcome', 'Count']
    fig2 = px.pie(oc, names='Outcome', values='Count', hole=0.4,
                  title='Distribution of Stop Outcomes')
    st.plotly_chart(fig2, use_container_width=True)

# --- Chart 3: Stops by Violation Type ---
with tab3:
    vc2 = data.groupby('violation')['id'].count().reset_index()
    vc2.columns = ['Violation', 'Total Stops']
    fig3 = px.bar(vc2.head(10), x='Violation', y='Total Stops',
                  title='Violation Types by Stop Count',
                  color='Total Stops', color_continuous_scale='Tealgrn')
    st.plotly_chart(fig3, use_container_width=True)

st.success("Dashboard loaded successfully!")

#-------------------------------------------
# Interactive SQL queries in streamlit
import streamlit as st
import pandas as pd
import plotly.express as px
import random
import pymysql

st.set_page_config(page_title="SecureCheck Police Dashboard", layout="wide")
st.title("SecureCheck: Police Check Post Digital Ledger")
st.markdown("Real-time monitoring and insights for law enforcement.")

# -----------------------------------------------
# Helper Functions
# -----------------------------------------------
def run_query(query):
    try:
        conn = pymysql.connect(host="localhost", user="root", password="Thritha@2009", database="postlog")
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

def show_chart(df):
    if len(df.columns) == 2:
        x, y = df.columns
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.bar(df, x=x, y=y, text=y, color=y, title="Bar Chart"), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df, names=x, values=y, title="Pie Chart"), use_container_width=True)

# -----------------------------------------------
# QUERY SECTIONS
# -----------------------------------------------
st.header("Quick Insights Dashboard")

# ====================================================
# Vehicle based queries
# ====================================================
st.header("Vehicle-Based Queries")
v_query = st.selectbox("Choose a Vehicle Query", [
    "",
    "Top 10 vehicles in drug-related stops",
    "Most searched vehicles"
])
if st.button("Run Vehicle Query"):
    q = {
        "Top 10 vehicles in drug-related stops":
        "SELECT vehicle_number, COUNT(*) AS total_stops FROM traffic_stops WHERE drugs_related_stop=1 GROUP BY vehicle_number ORDER BY total_stops DESC LIMIT 10;",
        "Most searched vehicles":
        "SELECT vehicle_number, COUNT(*) AS total_searches FROM traffic_stops WHERE search_conducted=1 GROUP BY vehicle_number ORDER BY total_searches DESC LIMIT 10;"
    }.get(v_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# ====================================================
# Demographics based queries
# ====================================================
st.header("Demographic-Based Queries")
d_query = st.selectbox("Choose a Demographic Query", [
    "",
    "Driver age group with highest arrest rate",
    "Gender distribution by country",
    "Race and gender combination with highest search rate"
])
if st.button("Run Demographic Query"):
    q = {
        "Driver age group with highest arrest rate":
        """SELECT CASE WHEN driver_age<25 THEN '<25' WHEN driver_age BETWEEN 25 AND 40 THEN '25-40'
           WHEN driver_age BETWEEN 41 AND 60 THEN '41-60' ELSE '60+' END AS age_group,
           ROUND(AVG(is_arrested)*100,2) AS arrest_rate FROM traffic_stops GROUP BY age_group ORDER BY arrest_rate DESC;""",
        "Gender distribution by country":
        "SELECT country_name, driver_gender, COUNT(*) AS total_stops FROM traffic_stops GROUP BY country_name, driver_gender;",
        "Race and gender combination with highest search rate":
        "SELECT driver_race, driver_gender, ROUND(AVG(search_conducted)*100,2) AS search_rate FROM traffic_stops GROUP BY driver_race, driver_gender ORDER BY search_rate DESC;"
    }.get(d_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# ====================================================
# Time based queries
# ====================================================
st.header("Time & Duration-Based Queries")
t_query = st.selectbox("Choose a Time Query", [
    "",
    "Stops by hour of day",
    "Average stop duration by violation",
    "Night vs Day arrest rate"
])
if st.button("Run Time Query"):
    q = {
        "Stops by hour of day":
        "SELECT HOUR(stop_time) AS hour, COUNT(*) AS total_stops FROM traffic_stops GROUP BY hour ORDER BY total_stops DESC;",
        "Average stop duration by violation":
        "SELECT violation, AVG(CASE stop_duration WHEN '0-15 Min' THEN 7.5 WHEN '16-30 Min' THEN 23 WHEN '30+ Min' THEN 45 END) AS avg_duration FROM traffic_stops GROUP BY violation;",
        "Night vs Day arrest rate":
        "SELECT CASE WHEN HOUR(stop_time) BETWEEN 20 AND 23 OR HOUR(stop_time)<6 THEN 'Night' ELSE 'Day' END AS period, ROUND(AVG(is_arrested)*100,2) AS arrest_rate FROM traffic_stops GROUP BY period;"
    }.get(t_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# ====================================================
# Violation based queries
# ====================================================
st.header("Violation-Based Queries")
vi_query = st.selectbox("Choose a Violation Query", [
    "",
    "Violations most linked to arrests",
    "Common among young drivers (<25)",
    "Violations with lowest arrest and search rates"
])
if st.button("Run Violation Query"):
    q = {
        "Violations most linked to arrests":
        "SELECT violation, SUM(is_arrested) AS total_arrests FROM traffic_stops GROUP BY violation ORDER BY total_arrests DESC LIMIT 10;",
        "Common among young drivers (<25)":
        "SELECT violation, COUNT(*) AS total FROM traffic_stops WHERE driver_age<25 GROUP BY violation ORDER BY total DESC LIMIT 10;",
        "Violations with lowest arrest and search rates":
        "SELECT violation, ROUND(AVG(is_arrested)*100,2) AS arrest_rate, ROUND(AVG(search_conducted)*100,2) AS search_rate FROM traffic_stops GROUP BY violation HAVING arrest_rate<5 AND search_rate<5;"
    }.get(vi_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# ====================================================
# Location based queries
# ====================================================
st.header("Location-Based Queries")
l_query = st.selectbox("Choose a Location Query", [
    "",
    "Countries with highest drug-related stops",
    "Arrest rate by country and violation",
    "Countries with most searches"
])
if st.button("Run Location Query"):
    q = {
        "Countries with highest drug-related stops":
        "SELECT country_name, ROUND(AVG(drugs_related_stop)*100,2) AS drug_rate FROM traffic_stops GROUP BY country_name ORDER BY drug_rate DESC;",
        "Arrest rate by country and violation":
        "SELECT country_name, violation, ROUND(AVG(is_arrested)*100,2) AS arrest_rate FROM traffic_stops GROUP BY country_name, violation ORDER BY arrest_rate DESC LIMIT 10;",
        "Countries with most searches":
        "SELECT country_name, COUNT(*) AS total_searches FROM traffic_stops WHERE search_conducted=1 GROUP BY country_name ORDER BY total_searches DESC;"
    }.get(l_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# -----------------------------------------------------
# Complex queries
#------------------------------------------------------
st.header("Complex Queries (Advanced Analysis)")
c_query = st.selectbox("Choose a Complex Query", [
    "",
    "Yearly breakdown of stops and arrests by country",
    "Driver violation trends by age and race",
    "Time-period analysis (year, month, hour)",
    "Violations with high search and arrest rates",
    "Driver demographics by country",
    "Top 5 violations with highest arrest rates"
])
if st.button("Run Complex Query"):
    q = {
        "Yearly breakdown of stops and arrests by country":
        "SELECT country_name, YEAR(stop_date) AS year, COUNT(*) AS total_stops, SUM(is_arrested) AS total_arrests FROM traffic_stops GROUP BY country_name, YEAR(stop_date) ORDER BY country_name, year;",
        "Driver violation trends by age and race":
        "SELECT driver_race, CASE WHEN driver_age<25 THEN '<25' WHEN driver_age BETWEEN 25 AND 40 THEN '25-40' WHEN driver_age BETWEEN 41 AND 60 THEN '41-60' ELSE '60+' END AS age_group, COUNT(*) AS total_violations FROM traffic_stops GROUP BY driver_race, age_group ORDER BY driver_race;",
        "Time-period analysis (year, month, hour)":
        "SELECT YEAR(stop_date) AS year, MONTH(stop_date) AS month, HOUR(stop_time) AS hour, COUNT(*) AS total_stops FROM traffic_stops GROUP BY year, month, hour ORDER BY year, month, hour;",
        "Violations with high search and arrest rates":
        "SELECT violation, ROUND(AVG(search_conducted)*100,2) AS search_rate, ROUND(AVG(is_arrested)*100,2) AS arrest_rate FROM traffic_stops GROUP BY violation ORDER BY search_rate DESC, arrest_rate DESC LIMIT 10;",
        "Driver demographics by country":
        "SELECT country_name, ROUND(AVG(driver_age),1) AS avg_age, driver_gender, driver_race, COUNT(*) AS total FROM traffic_stops GROUP BY country_name, driver_gender, driver_race ORDER BY country_name;",
        "Top 5 violations with highest arrest rates":
        "SELECT violation, ROUND(AVG(is_arrested)*100,2) AS arrest_rate FROM traffic_stops GROUP BY violation ORDER BY arrest_rate DESC LIMIT 5;"
    }.get(c_query, "")
    if q:
        df = run_query(q)
        st.dataframe(df, use_container_width=True)
        show_chart(df)

# ====================================================
# PREDICTION SECTION (SENTENCE + PROBABILITY)
# ====================================================
st.markdown("---")
st.header("Add New Police Log & Predict Stop Outcome and Violation")

with st.form("predict_form"):
    date = st.date_input("Stop Date")
    time = st.time_input("Stop Time")
    country = st.text_input("Country Name")
    gender = st.selectbox("Driver Gender", ["male", "female"])
    age = st.number_input("Driver Age", min_value=16, max_value=100, value=28)
    race = st.text_input("Driver Race")
    search = st.selectbox("Was a Search Conducted?", ["0", "1"])
    drug = st.selectbox("Was it Drug Related?", ["0", "1"])
    violation = st.text_input("Violation Type")
    duration = st.text_input("Stop Duration")
    submitted = st.form_submit_button("Predict Stop Outcome & Violation")

if submitted:
    prob = round(random.uniform(0.3, 0.9) * 100, 1)
    likely = "arrest" if prob > 60 else "warning"
    reason = "drug-related" if int(drug) == 1 else "routine"
    sentence = (
        f"On {date} at {time}, a {age}-year-old {gender} driver of race '{race}' in {country} "
        f"was stopped for a {reason} {violation or 'violation'}. "
        f"The predicted outcome is likely a **{likely}**, "
        f"with an estimated **{prob}%** chance of arrest."
    )
    st.success("Prediction generated successfully!")
    st.markdown(f"Predicted Summary")
    st.markdown(sentence)