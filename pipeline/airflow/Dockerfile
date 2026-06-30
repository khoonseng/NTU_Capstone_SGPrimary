FROM apache/airflow:3.2.1

# libgomp1 — GNU OpenMP runtime required by LightGBM for parallel computation.
# Must be installed as root before switching to the airflow user.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies needed by BashOperator tasks.
# All scraper scripts (scrape_sgschooling.py, load_sgschooling_data.py,
# load_schools_data.py) and the dbt build command run as shell calls
# from within this image — their Python imports must be available here.
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
