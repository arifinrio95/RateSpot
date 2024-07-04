import streamlit as st
import requests
import time
import pandas as pd
import numpy as np
import plotly.express as px
from playwright.sync_api import sync_playwright
from PIL import Image
import io
import subprocess
import sys

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

# Fungsi-fungsi untuk pembuatan poster
def create_star_svg(percentage):
    return f'''
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="star-{percentage}">
                <stop offset="{percentage}%" stop-color="#F2C94C" />
                <stop offset="{percentage}%" stop-color="#E0E0E0" />
            </linearGradient>
        </defs>
        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
              fill="url(#star-{percentage})" stroke="#F2C94C" stroke-width="1" />
    </svg>
    '''

def create_coffee_shops_poster(df, query, location):
    shops_html = ""
    for index, row in df.iterrows():
        stars_html = ''.join([create_star_svg(max(0, min(100, (row['rating'] - i) * 100))) for i in range(5)])
        shops_html += f'''
        <div class="bg-[#E4D5B7] p-4 rounded-lg shadow-md mb-4">
            <div class="flex justify-between items-center">
                <span class="font-semibold text-xl text-[#4A321E]">{row['rank']}. {row['name']}</span>
                <div class="flex items-center">
                    <div class="flex mr-2">{stars_html}</div>
                    <span class="font-medium text-lg text-[#4A321E]">{row['rating']:.1f}</span>
                </div>
            </div>
            <div class="text-sm text-[#6F4E37] mt-1">{row['user_ratings_total']:,} ratings</div>
        </div>
        '''

    dynamic_title = f"Top 10 {query} di {location}"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="bg-[#C1A87D] p-6 min-h-screen flex flex-col items-center justify-start font-sans" style="width: 900px;">
            <h1 class="text-4xl font-bold mb-6 text-[#4A321E] text-center">{dynamic_title}</h1>
            <div class="space-y-4 w-full max-w-3xl">
                {shops_html}
            </div>
            <div class="mt-6 text-sm text-[#4A321E]">Data based on user ratings and reviews</div>
        </div>
    </body>
    </html>
    '''

# Fungsi untuk menginstal Chromium
def install_chromium():
    try:
        # st.write("Installing Chromium...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                                capture_output=True, text=True, check=True)
        # st.write("Chromium installed successfully.")
        st.write(result.stdout)
    except subprocess.CalledProcessError as e:
        st.error("Failed to install Chromium.")
        st.error(e.stderr)
        raise
        
# Fungsi untuk generate poster
def generate_poster(df, query, location):
    html_content = create_coffee_shops_poster(df, query, location)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(chromium_sandbox=False)
            page = browser.new_page()
            page.set_content(html_content)
            
            # Set a larger initial viewport
            page.set_viewport_size({"width": 900, "height": 1500})
            
            # Get the full height of the content
            full_height = page.evaluate('() => document.body.scrollHeight')
            
            # Update the viewport and take the screenshot
            page.set_viewport_size({"width": 900, "height": full_height})
            screenshot_bytes = page.screenshot(full_page=True)
            
            browser.close()
        return screenshot_bytes
    except Exception as e:
        st.error(f"Error generating poster: {str(e)}")
        return None

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
        # df = df[df['rating'] > 4.2]
        # df = df[df['user_ratings_total'] > 100]

        # # Lakukan min-max scaling pada kolom user_ratings_total dan rating
        # df['scaled_ratings'] = min_max_scale(df['user_ratings_total'])
        # df['scaled_rating'] = min_max_scale(df['rating'])
        
        # # Hitung skor berdasarkan perkalian kedua nilai yang telah di-scale
        # df['score'] = df['scaled_ratings'] * df['scaled_rating']

        # Hitung geometric mean dari nilai yang telah di-scale
        df['score'] = np.sqrt(df['user_ratings_total'] * df['rating'])
        
        # Urutkan dataframe berdasarkan skor, dari yang tertinggi ke terendah
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        

        # st.write(f"\nTotal places after filtering (rating > 4.2 and user_ratings_total > 100): {len(df)}")

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

        # # Create scatter plot
        # st.write("Scatter Plot: Number of Reviews vs Rating")
        # fig = px.scatter(df, x='user_ratings_total', y='rating', hover_name='name',
        #                  labels={'user_ratings_total': 'Number of Reviews', 'rating': 'Rating'},
        #                  title=f'Rating vs Number of Reviews for {query} in {location}')
        # fig.update_layout(height=600)
        # st.plotly_chart(fig, use_container_width=True)

        # Bagian untuk generate poster
        
        try:
            install_chromium()  # Coba instal Chromium
            with st.spinner("Generating poster..."):
                screenshot_bytes = generate_poster(df_top10, query, location)
                if screenshot_bytes:
                    image = Image.open(io.BytesIO(screenshot_bytes))
                    st.image(image, caption="Generated Poster", use_column_width=True)
                    st.download_button(
                        label="Download Poster",
                        data=screenshot_bytes,
                        file_name=f"top10_{query.lower()}_{location.lower().replace(' ', '_')}_poster.png",
                        mime="image/png"
                    )
                else:
                    st.error("Failed to generate poster.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
                

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
