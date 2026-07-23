# -*- coding: utf-8 -*-
"""

@author: Davis Magee
Email: Davis.magee01@gmail.com
X (formerly Twitter): @DavisMagee_Wx
"""

# Importing the necessary libraries
import matplotlib.pyplot as plt
import numpy as np
import requests
import json
from datetime import datetime
import time

# Function to get station ID from user input
def get_station_id():
    print("NOAA NCEI Climate Data Download")
    print("=" * 40)
    
    # Requesting the station from the user
    custom_id = input("Enter the station ID (e.g., USW00003937): ").strip()
    return custom_id

# Function to get station name for display purposes
def get_station_name():
    return input("Enter the station name (e.g., Lake Charles Regional Airport): ").strip()

# Function to get date range from user
def get_date_range():
    print("\nDate Range Selection")
    print("=" * 40)
    
    current_year = datetime.now().year
    # Get start year
    while True:
        try:
            start_year = int(input(f"Enter start year (e.g., 1965): "))
            if 1800 <= start_year <= current_year:
                break
            else:
                print(f"Please enter a year between 1800 and {current_year}")
        except ValueError:
            print("Please enter a valid year")
    
    # Get end year
    while True:
        try:
            end_year = int(input(f"Enter end season (e.g., {current_year}): "))
            if start_year <= end_year <= current_year:
                break
            else:
                print(f"Please enter a year between {start_year} and {current_year}")
        except ValueError:
            print("Please enter a valid year")
    
    start_date = f"{start_year}-06-01"
    true_end = end_year + 1
    end_date = f"{true_end}-06-01"
    
    return start_date, end_date, start_year, end_year

# Function to split date range into smaller chunks
def split_date_range(start_date, end_date, years_per_chunk=10):
    """Split a large date range into smaller chunks"""
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    
    chunks = []
    current_start = start_year
    
    while current_start <= end_year:
        current_end = min(current_start + years_per_chunk - 1, end_year)
        chunk_start = f"{current_start}-01-01"
        chunk_end = f"{current_end}-12-31"
        chunks.append((chunk_start, chunk_end))
        current_start = current_end + 1
    
    print(f"Split {start_year}-{end_year} into {len(chunks)} chunks of up to {years_per_chunk} years each")
    return chunks

# Function to fetch data from NOAA NCEI API with chunking
def fetch_noaa_data_chunked(station_id, start_date, end_date, years_per_chunk=10):
    """Fetch data in chunks to handle large date ranges"""
    # Split the date range into chunks
    date_chunks = split_date_range(start_date, end_date, years_per_chunk)
    
    all_data = []
    total_records = 0
    
    for i, (chunk_start, chunk_end) in enumerate(date_chunks, 1):
        print(f"\nFetching chunk {i}/{len(date_chunks)}: {chunk_start} to {chunk_end}")
        
        chunk_data = fetch_noaa_data_single(station_id, chunk_start, chunk_end)
        
        if chunk_data:
            all_data.extend(chunk_data)
            total_records += len(chunk_data)
            print(f"Chunk {i}: Retrieved {len(chunk_data)} records")
        else:
            print(f"Warning: No data retrieved for chunk {i}")
        
        # Add a small delay between requests to be respectful to the API
        if i < len(date_chunks):
            time.sleep(1)
    
    print(f"\nTotal records retrieved across all chunks: {total_records}")
    return all_data, station_id

# Function to fetch single chunk of data
def fetch_noaa_data_single(station_id, start_date, end_date):
    """Fetch data for a single date range chunk"""
    base_url = "https://www.ncei.noaa.gov/access/services/data/v1"
    
    params = {
        'dataset': 'daily-summaries',
        'stations': station_id,
        'startDate': start_date,
        'endDate': end_date,
        'dataTypes': 'TMIN,RHAV',
        'units': 'standard',
        'format': 'json',
        'includeAttributes': 'false'
    }
    
    try:
        response = requests.get(f"{base_url}", params=params, timeout=60)
        
        if response.status_code != 200:
            print(f"API returned error: {response.status_code}")
            return None
        
        data = response.json()
        
        if not data:
            print(f"No data found for {start_date} to {end_date}")
            return None
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {start_date}-{end_date}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None

# Process the fetched data
def process_data(data):
    dates = []
    tmins = []
    rhav = []
    
    records_processed = 0
    records_with_tmin = 0
    records_with_rhav = 0
    
    for record in data:
        records_processed += 1
        date = record.get('DATE', '')
        tmin_str = record.get('TMIN', '')
        rhav_str = record.get('RHAV', '')
        
        if date and tmin_str and tmin_str.strip():
            try:
                # Convert temperature to integer
                tmin_value = int(float(tmin_str))
                dates.append(date.replace('-', ''))  # Format as YYYYMMDD
                tmins.append(tmin_value)
                records_with_tmin += 1
            except (ValueError, TypeError) as e:
                # Skip records with invalid temperature data
                continue
            
        if date and rhav_str and rhav_str.strip():
            try:
                # Convert relative humidity to integer
                rhav_value = int(float(rhav_str))
                rhav.append(rhav_value)
                records_with_rhav += 1
            except (ValueError, TypeError) as e:
                # Skip records with invalid relative humidity data
                continue
    
    print(f"Processed {records_processed} records, found {records_with_tmin} with TMIN data, found {records_with_rhav} with RHAV data")
    return dates, tmins, rhav

# Function to validate data quality
def validate_data(dates, tmins):
    """Basic validation of the retrieved data"""
    if not dates:
        return False
    
    # Check for data gaps
    try:
        date_objects = [datetime.strptime(date, '%Y%m%d') for date in dates]
        date_objects.sort()
        
        # Calculate date range
        start_date = date_objects[0]
        end_date = date_objects[-1]
        total_days = (end_date - start_date).days + 1
        
        print(f"Data covers {len(dates)} days out of {total_days} possible days ({len(dates)/total_days*100:.1f}% coverage)")
        
        # Check for reasonable temperature range
        min_temp = min(tmins)
        max_temp = max(tmins)
        print(f"Temperature range: {min_temp}°F to {max_temp}°F")
        
        return True
    except Exception as e:
        print(f"Error during data validation: {e}")
        return True  # Continue even if validation fails

# Function to calculate average humidt for the station
def calculate_average_humidity(rhav_values):
    """
    Calculate average relative humidity from the RHAV values collected
    during processing. Only considers records where RHAV was present
    and valid (already filtered by process_data).
    """
    # FIX: function now takes the humidity list as a parameter instead
    # of referring to undefined names (rhav, rhav_values, data)
    if not rhav_values:
        print("No valid RHAV values found in data")
        return None
    
    avg_humidity = sum(rhav_values) / len(rhav_values)
    
    print(f"Average RH calculated from {len(rhav_values)} records")
    
    return avg_humidity

def main():
    print("NOAA Climate Data Analysis - Days Below Freezing")
    print("=" * 50)
    
    # Get station information from user
    station_id = get_station_id()
    station_name = get_station_name()
    
    start_date, end_date, start_year, end_year = get_date_range()
    
    # Calculate total years and determine chunk size
    total_years = end_year - start_year + 1
    if total_years > 20:
        years_per_chunk = 10
    elif total_years > 10:
        years_per_chunk = 5
    else:
        years_per_chunk = total_years
    
    print(f"\nFetching {total_years} years of data in chunks of {years_per_chunk} years...")
    print(f"Station: {station_name} (ID: {station_id})")
    
    # Fetch data from NOAA with chunking
    data, actual_station_id = fetch_noaa_data_chunked(station_id, start_date, end_date, years_per_chunk)
    
    if not data:
        print("Failed to retrieve data. Let's try some troubleshooting:")
        print("1. Verify the station ID at: https://www.ncei.noaa.gov/access/search/")
        print("2. Try a smaller date range first")
        print("3. Check if the station has daily summary data")
        print("4. Try using just the station ID without any prefixes")
        return
    
    # Process the data
    dates, tmins, rhav = process_data(data)
    
    if not dates:
        print("No valid temperature data found in the response.")
        if data and len(data) > 0:
            print("Available fields in first record:", list(data[0].keys()))
        return
    
    # Validate data quality
    validate_data(dates, tmins)
    
    print(f"Successfully processed {len(dates)} records with minimum temperature data")
    
    avg_humidity = calculate_average_humidity(rhav)
    
    # Continue with original processing logic...
    years_in_data = []
    days_below_freezing = []

    def get_year_month(date_str):
        year = int(date_str[:4])
        month = int(date_str[4:6])
        return year, month

    current_winter_start_year = None
    current_winter_days = 0

    for i in range(len(dates)):
        date_str = dates[i]
        temp = tmins[i]
        
        year, month = get_year_month(date_str)

        if month >= 8:
            winter_start_year = year
        elif month <= 4:
            winter_start_year = year - 1
        else:
            continue
        
        if current_winter_start_year is None:
            if month >= 8:
                current_winter_start_year = winter_start_year
            else:
                continue
        
        if winter_start_year != current_winter_start_year:
            days_below_freezing.append(current_winter_days)
            years_in_data.append(current_winter_start_year)
            
            current_winter_start_year = winter_start_year
            current_winter_days = 0
        
        if temp <= 32:
            current_winter_days += 1

    # Check if we have data to plot
    if not years_in_data:
        print("No winter season data available for the specified range.")
        return

    # Creating a trend line
    trend_line = None
    slope = None
    
    if len(years_in_data) > 1:
        slope, intercept = np.polyfit(years_in_data, days_below_freezing, 1)
        trend_line = slope * np.array(years_in_data) + intercept
        print(f"The slope of the trend line is: {slope:.4f}")
        trend_label = f'Trend Line (slope: {slope:.4f})'
    else:
        print("Not enough data points for trend analysis")
        trend_label = ''
        
    # Printing the average Relative Humidity
    if calculate_average_humidity is not None:
        print(f"Average relative humidity: {avg_humidity:.2f}%")
    else:
        print("No relative humidity data available for this station/date range")        

    # Plotting the data
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(years_in_data, days_below_freezing, linestyle='-', color='b', 
            marker='o', markersize=4, label="Days Below Freezing")

    # Check if trend_line exists and has data
    if trend_line is not None and len(trend_line) > 0:
        ax.plot(years_in_data, trend_line, linestyle='--', color='r', 
                label=trend_label)

    # Set x-axis ticks
    if years_in_data:
        x_min = min(years_in_data)
        x_max = max(years_in_data)
        tick_interval = max(5, (x_max - x_min) // 10)
        plt.xticks(np.arange(x_min, x_max + 2, tick_interval))

    plt.ylim(ymin=0)

    # Add labels and title - using the custom station name
    ax.set_xlabel("Winter Season (Starting Year)")
    ax.set_ylabel('Days Below Freezing')
    ax.set_title(f'Days Below Freezing over Years\n{station_name} ({start_year} - {end_year})')

    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
if __name__ == "__main__":
    main()
