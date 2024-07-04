import streamlit as st
import requests
import time
import pandas as pd
import numpy as np

# Function to search for places
def search_places(api_key, query, location):
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    places = []
    next_page_token = None

    while True:
        params = {
            'query': f'{query} in {location}',
            'key': api_key
        }
        if next_page_token:
            params['pagetoken'] = next_page_token

        response = requests.get(base_url, params=params)
        result = response.json()

        if 'results' in result:
            places.extend(result['results'])
            st.write(f"Fetched {len(result['results'])} places. Total: {len(places)}")

        if 'next_page_token' in result:
            next_page_token = result['next_page_token']
            time.sleep(2)  # Wait for the next_page_token to become valid
        else:
            break

    return places

# Function to get place details
def get_place_details(api_key, place_id):
    base_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'name,rating,user_ratings_total,formatted_address,formatted_phone_number,website,price_level,opening_hours,reviews',
        'key': api_key
    }

    response = requests.get(base_url, params=params)
    result = response.json()

    return result.get('result', {})

# Main Streamlit app
def main():
    st.title("Google Places Search App")

    # Get API key from Streamlit secrets
    api_key = st.secrets["google_places_api_key"]

    # User inputs
    location = st.text_input("Enter location", "Purwokerto")
    query = st.text_input("Enter place type", "Coffee Shop")

    if st.button("Search"):
        places = search_places(api_key, query, location)

        st.write(f"\nTotal places found: {len(places)}")

        data = []
        progress_bar = st.progress(0)
        for i, place in enumerate(places, 1):
            progress_bar.progress(i / len(places))
            details = get_place_details(api_key, place['place_id'])

            place_data = {
                'name': details.get('name', 'N/A'),
                'rating': details.get('rating', np.nan),
                'user_ratings_total': details.get('user_ratings_total', 0),
                'address': details.get('formatted_address', 'N/A'),
                'phone': details.get('formatted_phone_number', 'N/A'),
                'website': details.get('website', 'N/A'),
                'price_level': details.get('price_level', 'N/A'),
                'open_now': details.get('opening_hours', {}).get('open_now', 'N/A'),
                'latitude': place['geometry']['location']['lat'],
                'longitude': place['geometry']['location']['lng'],
            }

            if 'reviews' in details and len(details['reviews']) > 0:
                first_review = details['reviews'][0]
                place_data.update({
                    'review_rating': first_review.get('rating', np.nan),
                    'review_text': first_review.get('text', 'N/A')[:100] + '...',
                    'review_time': first_review.get('relative_time_description', 'N/A')
                })

            data.append(place_data)

        df = pd.DataFrame(data)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['user_ratings_total'] = pd.to_numeric(df['user_ratings_total'], errors='coerce')

        df = df.sort_values(by='user_ratings_total', ascending=False)
        df = df[df['rating'] > 4.2]
        df = df[df['user_ratings_total'] > 100]

        st.write(f"\nTotal places after filtering (rating > 4.2 and user_ratings_total > 100): {len(df)}")

        df_top10 = df[['name', 'rating', 'user_ratings_total', 'address']].head(10).sort_values(by=['rating'], ascending=False)
        df_top10 = df_top10.reset_index(drop=True)
        df_top10['rank'] = df_top10.index + 1

        # Display top 10 places
        st.write("Top 10 Places:")
        st.dataframe(df_top10[['rank', 'name', 'rating', 'user_ratings_total', 'address']], 
                     height=400, 
                     use_container_width=True)

        # Download button for full data
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download full data as CSV",
            data=csv,
            file_name=f'{query.lower()}_{location.lower().replace(" ", "_")}_filtered.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
