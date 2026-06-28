FROM apache/airflow:3.2.1

# Install project dependencies needed by BashOperator tasks.
# All scraper scripts (scrape_sgschooling.py, load_sgschooling_data.py,
# load_schools_data.py) and the dbt build command run as shell calls
# from within this image — their Python imports must be available here.
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
