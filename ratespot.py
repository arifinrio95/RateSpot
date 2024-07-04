import streamlit as st
import requests
import time
import pandas as pd
import numpy as np
import plotly.express as px

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

def min_max_scale(series):
    return (series - series.min()) / (series.max() - series.min())

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

        # df['score'] = df['user_ratings_total']*df['rating']
        # df = df.sort_values(by=['rating', 'user_ratings_total'], ascending=[False, False])
        df = df[df['rating'] > 4.2]
        df = df[df['user_ratings_total'] > 100]

        # # Lakukan min-max scaling pada kolom user_ratings_total dan rating
        # df['scaled_ratings'] = min_max_scale(df['user_ratings_total'])
        # df['scaled_rating'] = min_max_scale(df['rating'])
        
        # # Hitung skor berdasarkan perkalian kedua nilai yang telah di-scale
        # df['score'] = df['scaled_ratings'] * df['scaled_rating']

        # Hitung geometric mean dari nilai yang telah di-scale
        df['score'] = np.sqrt(df['user_ratings_total'] * df['rating'])
        
        # Urutkan dataframe berdasarkan skor, dari yang tertinggi ke terendah
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        

        st.write(f"\nTotal places after filtering (rating > 4.2 and user_ratings_total > 100): {len(df)}")

        df_top10 = df[['name', 'rating', 'user_ratings_total', 'address','price_level']].head(10)

        
        df_top10 = df_top10.reset_index(drop=True)
        df_top10['rank'] = df_top10.index + 1

        # Display top 10 places
        st.header("Top 10 Places:")
        st.write("The top 10 places are selected based on criteria of having a rating above 4.2 and more than 100 reviews. This list is then sorted according to the Geometric Mean of rating value and number of reviews.")
        df_top10_renamed = df_top10.rename(columns={
                                'name': 'Nama Tempat',
                                'rating': 'Rating',
                                'user_ratings_total': 'Jumlah Ulasan',
                                'address': 'Alamat',
                                'price_level': 'Tingkat Harga'
                            })
        st.dataframe(df_top10_renamed, 
                     height=400, 
                     use_container_width=True)

        # Create scatter plot
        st.write("Scatter Plot: Number of Reviews vs Rating")
        fig = px.scatter(df, x='user_ratings_total', y='rating', hover_name='name',
                         labels={'user_ratings_total': 'Number of Reviews', 'rating': 'Rating'},
                         title=f'Rating vs Number of Reviews for {query} in {location}')
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

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
