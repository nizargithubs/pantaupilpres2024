import json
import requests
import pandas as pd
import numpy as np
import streamlit as st

from datetime import datetime
import pytz

# Mendapatkan zona waktu Jakarta
jakarta_timezone = pytz.timezone('Asia/Jakarta')

# Mendapatkan waktu saat ini di zona waktu Jakarta
current_datetime = datetime.now(jakarta_timezone).strftime("%d-%m-%Y %H:%M:%S")

# ---------------------------------------------------------------------------------------------------------------------------------------
# Link | Kawal Pemilu & Sirekap KPU
# ---------------------------------------------------------------------------------------------------------------------------------------
# Kawal Pemilu
logo_url_kawal_pemilu = "https://kawalpemilu.org/assets/kp.png"
url_kawal_pemilu = f"https://kawalpemilu.org/h/"

# Sirekap KPU
logo_url_sirekap_sirekap = "https://pemilu2024.kpu.go.id/assets/logo.7cbefe7d.png"
url_sirekap_sirekap = f"https://pemilu2024.kpu.go.id/pilpres/hitung-suara/"

def compare(id,tingkat):
    
    # ------------------------------------------------------------------------------------------
    # GET : data from api kawalpemilu.org
    # ------------------------------------------------------------------------------------------     
    
    if tingkat == 'kel':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)).json()

    elif tingkat == 'kec':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:6]).json()
    
    elif tingkat == 'kab':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:4]).json()

    elif tingkat == 'prov':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:2]).json()

    elif tingkat == 'dnegeri':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id=").json()

    elif tingkat == 'lnegeri':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:2]).json()

    aggregated_data = data["result"]["aggregated"]

    dfs = []
    for key, values in aggregated_data.items():
        df = pd.DataFrame(values)
        dfs.append(df)

    df = pd.concat(dfs,ignore_index=True)

    if tingkat == 'kel' :
        df = df[['idLokasi', 'pas1', 'pas2', 'pas3', 'dpt', 'name']].drop_duplicates(subset=['idLokasi'],keep='first')
    
    else: 
        df = df[['idLokasi', 'pas1', 'pas2', 'pas3', 'totalTps', 'name']].drop_duplicates(subset=['idLokasi'],keep='first')
        

    df['status'] = np.where((df['pas1'] == 0) & (df['pas2'] == 0) & (df['pas3'] == 0), 0, 1)
    
    if tingkat == 'kel' :
        df['idLokasi'] = id*1000 + df['name'].astype(int)   

    df['idLokasi'] = df['idLokasi'].astype(str)

    kawalpemilu = df

    # ------------------------------------------------------------------------------------------
    # GET : data from api sirekap kpu
    # ------------------------------------------------------------------------------------------    

    if tingkat == 'kel':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+"/"+str(id)[0:6]+"/"+str(id)+".json").json()
    
    elif tingkat == 'kec':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+"/"+str(id)[0:6]+".json").json()  
    
    elif tingkat == 'kab':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+".json").json()
    
    elif tingkat == 'prov':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+".json").json()
    
    elif tingkat == 'dnegeri':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp.json").json()

    elif tingkat == 'lnegeri':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+".json").json()

    rows = []

    for id_, values in data['table'].items():
        row = {
            'id': id_,
            'psu': values['psu'],
            'persen': values['persen'],
            'status_progress': values['status_progress']
        }
        # 01 - paslon 1
        if '100025' in values:
            row['100025'] = int(values['100025'])
        else: row['100025'] = 0
        
        # 02 - paslon 2
        if '100026' in values:
            row['100026'] = int(values['100026'])
        else: row['100026'] = 0  
        
        # 03 - paslon 3
        if '100027' in values:
            row['100027'] = int(values['100027'])
        else: row['100027'] = 0

        # persen
        if 'persen' in values:
            row['persen'] = values['persen']
        else: row['persen'] = 0

        # status
        if 'status_progress' in values:
            row['status_progress'] = values['status_progress']
        else: row['status_progress'] = 0

        rows.append(row)

    df = pd.DataFrame(rows)      
        
    df = df.rename(columns={'100025':'pas1','100026':'pas2','100027':'pas3','persen':'persen_sirekap'})
    df = df[['id','pas1','pas2','pas3','persen_sirekap']].fillna(0)

    df['pas1'] = df['pas1'].astype(int)
    df['pas2'] = df['pas2'].astype(int)
    df['pas3'] = df['pas3'].astype(int)
    df['persen_sirekap'] = df['persen_sirekap'].round(2).map('{:.2f}'.format)   
    
    df['status'] = np.where((df['pas1'] == 0) & (df['pas2'] == 0) & (df['pas3'] == 0), 0, 1)     
    
    kpu = df

    # -----------------------------------------------------------------------------------------------
    # COMPARISON
    # -----------------------------------------------------------------------------------------------
    def color_name(val):
        color = 'black'  # Warna default
        return f'color: {color}'

    if tingkat == 'kel' :          

        #merge data sirekap kpu with kawalpemilu.org
        compared = pd.merge(kawalpemilu, kpu, left_on='idLokasi', right_on='id', how='inner')   
        
        compared.columns = ['idLokasi', 
                            'pas1_kawal', 
                            'pas2_kawal', 
                            'pas3_kawal', 
                            'dpt', 
                            'tps', 
                            'status_kawal',
                            'id',                             
                            'pas1_sirekap', 
                            'pas2_sirekap', 
                            'pas3_sirekap', 
                            'persen_sirekap',
                            'status_sirekap'                            
                        ]       
        
        compared['tps'] = 'TPS ' + compared['tps'].astype(str).str.zfill(3)
        compared['dpt'] = compared['dpt'].round(0)
        compared = compared[
                        [                       
                            'tps',                           
                            'dpt',
                            'pas1_kawal', 
                            'pas2_kawal', 
                            'pas3_kawal',                                                        
                            'pas1_sirekap', 
                            'pas2_sirekap', 
                            'pas3_sirekap', 
                            'persen_sirekap',
                            'status_sirekap'                           
                        ]
                    ]  
        #persen_sirekap dengan desimal
        compared['persen_sirekap'] = compared['persen_sirekap'].round(2).astype(str)+ '%'

        # compare sirekap kpu with kawalpemilu.org
        def sah_sirekap(row):
            # kondisi sudah kawal
            if  row['status_sirekap'] == 1:
                #jumlah pas1_sirekap + pas2_sirekap + pas3_sirekap
                return row['pas1_sirekap'] + row['pas2_sirekap'] + row['pas3_sirekap']
            # kondisi : belum dikawal dan data kpu belum ada            
            else: 
                return '0' 
        
        compared['sah_sirekap'] = compared.apply(sah_sirekap, axis=1)

        # compare sirekap kpu with kawalpemilu.org
        def hasil_kawal(row):
            # kondisi sudah kawal
            if row['status_sirekap'] == 1:
                # kondisi sesuai
                if row['pas1_kawal'] == row['pas1_sirekap'] and row['pas2_kawal'] == row['pas2_sirekap'] and row['pas3_kawal'] == row['pas3_sirekap']:
                    return '✔️ sesuai' 
                # kondisi markup                
                elif row['pas1_sirekap'] + row['pas2_sirekap'] + row['pas3_sirekap'] > row['dpt']*1.02 or row['pas1_kawal'] + row['pas2_kawal'] + row['pas3_kawal'] > row['dpt']*1.02:
                    return '🚩markup' 
                # kondisi tidak sesuai
                else: return '❌ tidak sesuai' #detect ketidaksesuaian dengan kawalpemilu    
            # kondisi : belum dikawal dan data kpu belum ada            
            else: 
                # kondisi perlu dicek sirekap
                if row['pas1_kawal'] > row['pas1_sirekap'] and row['pas2_kawal'] > row['pas2_sirekap'] and row['pas3_kawal'] > row['pas3_sirekap']:
                    return '🔍 cek sirekap' 
                # kondisi tidak perlu dicek sirekap
                # kondisi belum dikawal
                else: return '⏳ belum dikawal' 
        
        compared['hasil_kawal'] = compared.apply(hasil_kawal, axis=1)

        #persen
        def persen(row):
            if row['hasil_kawal'] == '✔️ sesuai':
                return '100%'          
            elif row['hasil_kawal'] == '❌ tidak sesuai':
                return '0%'
            else: return '0%' #Belum dikawal'

        compared['persen_kawal'] = compared.apply(persen, axis=1)    

        #status_sirekap
        def status_sirekap(row):
            if row['status_sirekap']  == 1:
                # panggil persen_sirekap
                persen_sirekap = row['persen_sirekap']

                if persen_sirekap == '100.00%':
                    return f'🎉 Selesai' 
                elif persen_sirekap > '0.00%' and persen_sirekap < '100.00%':
                    return f'🚀 Progress'               
                else: return '❌ belum selesai'                   
                
            else: return '❌ belum dimulai'            

        compared['status_sirekap'] = compared.apply(status_sirekap, axis=1)          

        #info_kawal
        def info_kawal(row):
            if row['hasil_kawal']  == '✔️ sesuai':
                if row['pas1_sirekap'] > row['pas2_sirekap'] and row['pas1_sirekap'] > row['pas3_sirekap']:
                    return '🟩1️⃣'
                elif row['pas2_sirekap'] > row['pas1_sirekap'] and row['pas2_sirekap'] > row['pas3_sirekap']:
                    return '🟧2️⃣'
                elif row['pas3_sirekap'] > row['pas1_sirekap'] and row['pas3_sirekap'] > row['pas2_sirekap']:
                    return '🟥3️⃣'
                else:
                    return ''
            else:
                return ''

        compared['info_kawal'] = compared.apply(info_kawal, axis=1)     
    
    else:     
        #merge data sirekap kpu with kawalpemilu.org
        compared = pd.merge(kawalpemilu, kpu, left_on='idLokasi', right_on='id', how='inner')       
        
        compared.columns = [
                    'idLokasi', 
                    'pas1_kawal', 
                    'pas2_kawal', 
                    'pas3_kawal', 
                    'totalTps', 
                    'name', 
                    'status_kawal',
                    'id',                     
                    'pas1_sirekap', 
                    'pas2_sirekap', 
                    'pas3_sirekap', 
                    'persen_sirekap',
                    'status_sirekap'                    
                ]
        compared = compared[[                    
                    'name',
                    'totalTps',
                    'pas1_kawal', 
                    'pas2_kawal', 
                    'pas3_kawal',                    
                    'pas1_sirekap', 
                    'pas2_sirekap', 
                    'pas3_sirekap', 
                    'persen_sirekap',
                    'status_sirekap'                    
                ]]     
        
        #persen_sirekap dengan desimal
        compared['persen_sirekap'] = compared['persen_sirekap'].round(2).astype(str)+ '%'

        # Sah_
        def sah_sirekap(row):
            # kondisi sudah kawal
            if  row['status_sirekap'] == 1:
                #tidak boleh kosong
                if row['pas1_sirekap'] != 0 or row['pas2_sirekap'] != 0 or row['pas3_sirekap'] != 0:
                    return row['pas1_sirekap'] + row['pas2_sirekap'] + row['pas3_sirekap']
                else: 
                    return ''
            # kondisi : belum dikawal dan data kpu belum ada            
            else: 
                return '' 
        compared['sah_sirekap'] = compared.apply(sah_sirekap, axis=1)       

        #compare sirekap kpu with kawalpemilu.org
        def hasil_kawal(row):
            if row['status_sirekap'] == 1:            
                # kondisi sesuai dengan kawalpemilu
                if row['pas1_kawal'] == row['pas1_sirekap'] and row['pas2_kawal'] == row['pas2_sirekap'] and row['pas3_kawal'] == row['pas3_sirekap']:
                    return '✔️ sesuai'  
                # kondisi tidak sesuai dengan kawalpemilu
                else: return '❌ tidak sesuai'
            
            else: 
                return '⏳ belum dikawal' #detect tps belum dikawal/data belum ada di kawalpemilu
            
        compared['hasil_kawal'] = compared.apply(hasil_kawal, axis=1)             
        
        #status_sirekap
        def status_sirekap(row):
            if row['status_sirekap']  == 1:
                # panggil persen_sirekap
                persen_sirekap = row['persen_sirekap']

                if persen_sirekap == '100.00%':
                    return f'🎉 Selesai' 
                elif persen_sirekap > '0.00%' and persen_sirekap < '100.00%':
                    return f'🚀 Progress'               
                else: return '❌ belum selesai'                   
                
            else: return '❌ belum dimulai'            

        compared['status_sirekap'] = compared.apply(status_sirekap, axis=1)         

        def info_kawal(row):          
                if row['pas1_sirekap'] > row['pas2_sirekap'] and row['pas1_sirekap'] > row['pas3_sirekap']:
                    return '🟩1️⃣'
                elif row['pas2_sirekap'] > row['pas1_sirekap'] and row['pas2_sirekap'] > row['pas3_sirekap']:
                    return '🟧2️⃣'
                elif row['pas3_sirekap'] > row['pas1_sirekap'] and row['pas3_sirekap'] > row['pas2_sirekap']:
                    return '🟥3️⃣'
                else:
                    return ''            

        compared['info_kawal'] = compared.apply(info_kawal, axis=1) 
        

    return compared

# Fungsi untuk menambahkan warna baris berdasarkan kondisi
def row_color(row):
    color = '#a0f3b5' if row['hasil_kawal'] == '✔️ sesuai' else \
            '#f3cba0' if row['hasil_kawal'] == '⏳ belum dikawal' else \
            '#f3a0ab' if row['hasil_kawal'] == '❌ tidak sesuai' else '#e3e3e3'
    
    return [f'background-color: {color}'] * len(row)

# Fungsi untuk mewarnai baris sesuai kriteria tertentu
def row_color1(row):
    if row['name'] == 'LUAR NEGERI':
        color = '#d5cef7'
    else:
        color = '#a0f3b5' if row['hasil_kawal'] == '✔️ sesuai' else \
                '#f3cba0' if row['hasil_kawal'] == '⏳ belum dikawal' else \
                '#f3a0ab' if row['hasil_kawal'] == '❌ tidak sesuai' else '#e3e3e3'
        
    return [f'background-color: {color}'] * len(row)


def get_total_tps(data):
    if "progres" in data and "total" in data["progres"]:
        return data["progres"]["total"]
    
    else:
        return None
    
def get_total_progress(data):
    if "progres" in data and "progres" in data["progres"]:
        return data["progres"]["progres"]
    
    else:
        return None    

# ------------------------------------------------------------------------------------------
# Read Data
# ------------------------------------------------------------------------------------------
tps = pd.read_json("data.json",dtype=False)

st.set_page_config( 
    page_title="Pantau Pilpres 2024",   
    page_icon="🔍",
    initial_sidebar_state="expanded",       
    layout="wide"
)

st.header("🕵️ Pantau Pilpres 2024 ")
st.write(f"""<p style="margin-top: -5px; font-size: 16px;">Dibuat sebagai alat bantu untuk memantau suara di Sirekap KPU & KawalPemilu.org, update : {current_datetime} WIB</p>""", unsafe_allow_html=True)
st.write(f"""<p style="margin-top: -10px;margin-bottom: 15px;border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Suara Rekapitulasi","Suara TPS","Suara Wilayah","Suara Paslon 2024"])

# Nasional
with tab1:
    # ---------------------------------------------------------------------------------------------------------------------------------------
    st.subheader('Suara Rekapitulasi')
    st.write(f"""<p style="margin-top: -10px; margin-bottom: 25px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
    # ---------------------------------------------------------------------------------------------------------------------------------------

    # ---------------------------------------------------------------------------------------------------------------------------------------
    d1, d2, d3 = st.columns(3)
    # ---------------------------------------------------------------------------------------------------------------------------------------
    
    id_wil = 99

    tab_dalam_negeri, tab_luar_negeri = st.tabs(['Dalam Negeri','Luar Negeri'])
    
    with tab_dalam_negeri:

        
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.subheader('Dalam Negeri:')
        # ---------------------------------------------------------------------------------------------------------------------------------------
        x1, x2, x3 = st.columns([6,2,2])                
        
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Filter
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # x1.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        id = int(id_wil)

        # Menampilkan dataframe
        df_id_not_99 = compare(id_wil, tingkat = 'dnegeri')

        # Filter data untuk ID yang bukan 99
        df_filtered = df_id_not_99

        # Setelah mengurutkan DataFrame berdasarkan nama
        df_sorted_filtered = df_filtered.sort_values(by='name')
                
        # Atur ulang indeks DataFrame setelah pengurutan
        df_sorted_filtered = df_sorted_filtered.reset_index(drop=True)

        # Menambahkan kolom 'No'
        df_sorted_filtered.insert(0, 'No', df_sorted_filtered.index + 1)
      
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # URL untuk link tombol Kawal Pemilu & Sirekap KPU
        # ---------------------------------------------------------------------------------------------------------------------------------------      
        x2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(df_filtered)[0:2], use_container_width = True)
        x3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(df_filtered)[0:2], use_container_width = True) 
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Progress TPS
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # LUAR NEGERI
        url_ln = "https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/99.json"
        response_ln = requests.get(url_ln)
        data_ln = response_ln.json()

        # Mendapatkan nilai total progres - luar negeri
        total_progress_tps_ln = get_total_progress(data_ln)
        jumlah_tps_ln = get_total_tps(data_ln)
        # --------------------------------------------------------------------------------------
        # DALAM NEGERI
        url1 = "https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp.json"
        response1 = requests.get(url1)
        data1 = response1.json()       
        
        # Mendapatkan nilai total progres - dalam negeri
        total_progress_tps = get_total_progress(data1) #-total_progress_tps_ln

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total Provinsi
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total provinsi
        total_provinsi = df_sorted_filtered['totalTps'].count()-1

        # Memformat total provinsi dengan menambahkan koma sebagai pemisah ribuan
        total_provinsi_formatted = "{:,}".format(total_provinsi)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total TPS
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # TPS -> Jumlah
        jumlah_tps = get_total_tps(data1) #-jumlah_tps_ln

        # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_total_formatted = "{:,}".format(jumlah_tps)

        # TPS -> PROGRESS
        # Menghitung total jumlah TPS
        total_tps = total_progress_tps

        # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_formatted = "{:,}".format(total_tps)

        #persentase tps
        total_tps_percent = (total_tps / jumlah_tps) * 100

        #format persen
        total_tps_percent_formatted = f"{total_tps_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # SUARA SAH
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total jumlah Suara Sah
        total_sah = df_sorted_filtered['sah_sirekap'].sum()

        # Memformat total jumlah Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_sah_formatted = "{:,}".format(total_sah)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Tampilkan
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara Sah Dalam Negeri di <b> {total_provinsi_formatted} </b> Provinsi dan <b>1</b> Luar Negeri | TPS masuk <b> {total_tps_formatted} ({total_tps_percent_formatted}%) </b> dari Total TPS <b>{total_tps_total_formatted}</b> | Total Suara Sah <b> {total_sah_formatted} </b. </p>""", unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------------------------------
        # 01
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas1 = df_sorted_filtered['pas1_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas1_formatted = "{:,}".format(total_pas1)

        #persentase
        total_pas1_percent = (total_pas1 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas1_percent_formatted = f"{total_pas1_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 02
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas2 = df_sorted_filtered['pas2_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas2_formatted = "{:,}".format(total_pas2)

        #persentase
        total_pas2_percent = (total_pas2 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas2_percent_formatted = f"{total_pas2_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 03
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas3 = df_sorted_filtered['pas3_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas3_formatted = "{:,}".format(total_pas3)

        #persentase
        total_pas3_percent = (total_pas3 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas3_percent_formatted = f"{total_pas3_percent:.2f}"

        p1, p2, p3 = st.columns(3)

        with p1:
            st.header("01")
            p1a, p1b = st.columns([1,2])
            p1a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
            with p1b:               
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas1_formatted}</b> ({total_pas1_percent_formatted}%) </p>""", unsafe_allow_html=True)     
        
        with p2:
            st.header("02")
            p2a, p2b = st.columns([1,2])
            p2a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
            with p2b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas2_formatted}</b> ({total_pas2_percent_formatted}%) </p>""", unsafe_allow_html=True)
        
        with p3:
            st.header("03")
            p3a, p3b = st.columns([1,2])
            p3a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
            with p3b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas3_formatted}</b> ({total_pas3_percent_formatted}%) </p>""", unsafe_allow_html=True)
               
        st.dataframe(
            df_sorted_filtered.iloc[:40].style.apply(row_color1, axis=1),            
            height=1500,
            hide_index=True, 
            use_container_width=True
        )  
        
            
        #Menampilkan diagram batang
        st.subheader('📊 Diagram Suara:')
        x4, x5 = st.columns(2)
        # ---------------------------------------------------------------------------------------------
        x4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
        x4.area_chart(df_id_not_99[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kabupaten_kota'}), 
                    x='kabupaten_kota',
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        # ---------------------------------------------------------------------------------------------
        x5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
        x5.line_chart(df_id_not_99[['name','pas1_sirekap','pas2_sirekap', 'pas3_sirekap']].rename(columns={'name': 'kabupaten kota'}), 
                    x='kabupaten kota', 
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])      


    with tab_luar_negeri:
        # -- ------------------------------------------------------------------------------------------------------------
        st.subheader('Luar Negeri:')
        # --------------------------------------------------------------------------------------------------------------------------------------------
        y1, y2, y3 = st.columns([6,2,2])
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # URL untuk link tombol Kawal Pemilu & Sirekap KPU
        # ---------------------------------------------------------------------------------------------------------------------------------------      
        y2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(id_wil), use_container_width = True)
        y3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(id_wil)[0:2]+"/"+str(id_wil)[0:4], use_container_width = True)   

        # ---------------------------------------------------------------------------------------------------------------------------------------
        id = int(id_wil)
        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Menampilkan dataframe
        df_id_99 = compare(id_wil, tingkat = 'lnegeri')

        # Setelah mengurutkan DataFrame berdasarkan nama
        df_sorted_id_99 = df_id_99.sort_values(by='name')

       # Atur ulang indeks DataFrame setelah pengurutan
        df_sorted_id_99 = df_sorted_id_99.reset_index(drop=True)

       # Menambahkan kolom 'No'
        df_sorted_id_99.insert(0, 'No', df_sorted_id_99.index + 1)        

       # ---------------------------------------------------------------------------------------------------------------------------------------
       # TPS
       # ---------------------------------------------------------------------------------------------------------------------------------------
        url = "https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/99.json"
        response = requests.get(url)
        data = response.json()
       
        # Mendapatkan nilai total progres
        total_progress_tps_ln = get_total_progress(data)
        jumlah_tps_ln         = get_total_tps(data)

       # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_ln_total_formatted = "{:,}".format(jumlah_tps_ln)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total Negara
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total Negara
        total_ln = df_sorted_id_99['totalTps'].count()

       # Memformat total Negara dengan menambahkan koma sebagai pemisah ribuan
        total_ln_formatted = "{:,}".format(total_ln)       

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total TPS
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total jumlah TPS
        total_tps_ln = total_progress_tps_ln

        # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_ln_formatted = "{:,}".format(total_tps_ln)

        #persentase tps
        total_tps_ln_percent = (total_tps_ln / jumlah_tps_ln) * 100

        #format persen
        total_tps_ln_percent_formatted = f"{total_tps_ln_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # SUARA SAH
        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Menghitung total Suara Sah
        total_sah = df_sorted_id_99['sah_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_sah_formatted = "{:,}".format(total_sah)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Tampilkan
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara di Luar Negeri di <b>{total_ln_formatted}</b> Negara | TPS masuk <b> {total_tps_ln_formatted} ({total_tps_ln_percent_formatted}%) </b> dari Total TPS <b>{total_tps_ln_total_formatted}</b> | Total Suara Sah <b> {total_sah_formatted} </b>. </p>""", unsafe_allow_html=True)
        
        # ---------------------------------------------------------------------------------------------------------
        # 01
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas1 = df_sorted_id_99['pas1_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas1_formatted = "{:,}".format(total_pas1)

        #persentase
        total_pas1_percent = (total_pas1 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas1_percent_formatted = f"{total_pas1_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 02
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas2 = df_sorted_id_99['pas2_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas2_formatted = "{:,}".format(total_pas2)

        #persentase
        total_pas2_percent = (total_pas2 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas2_percent_formatted = f"{total_pas2_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 03
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas3 = df_sorted_id_99['pas3_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas3_formatted = "{:,}".format(total_pas3)

        #persentase
        total_pas3_percent = (total_pas3 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas3_percent_formatted = f"{total_pas3_percent:.2f}"

        p1, p2, p3 = st.columns(3)

        with p1:
            st.header("01")
            p1a, p1b = st.columns([1,2])
            p1a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
            with p1b:               
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas1_formatted}</b> ({total_pas1_percent_formatted}%) </p>""", unsafe_allow_html=True)     
        
        with p2:
            st.header("02")
            p2a, p2b = st.columns([1,2])
            p2a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
            with p2b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas2_formatted}</b> ({total_pas2_percent_formatted}%) </p>""", unsafe_allow_html=True)
        
        with p3:
            st.header("03")
            p3a, p3b = st.columns([1,2])
            p3a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
            with p3b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas3_formatted}</b> ({total_pas3_percent_formatted}%) </p>""", unsafe_allow_html=True)

        dataframe_id_99_display = st.dataframe(
            df_sorted_id_99.iloc[:100].style.apply(row_color, axis=1),
            height=3400,
            hide_index=True, 
            use_container_width=True
        )     
        
        #Menampilkan diagram batang
        st.subheader('📊 Diagram Suara:')
        y4, y5 = st.columns(2)
        # ----------------------------------------------------------------------------------------------------------------------------------------
        y4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
        y4.line_chart(df_sorted_id_99[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kecamatan'}), 
                    x='kecamatan',
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        # ----------------------------------------------------------------------------------------------------------------------------------------
        y5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
        y5.line_chart(df_sorted_id_99[['name','pas1_sirekap','pas2_sirekap','pas3_sirekap']].rename(columns={'name': 'kecamatan'}), 
                    x='kecamatan', 
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])       

# Per TPS
with tab2:
    # --------------------------------------------------------------------------------------------------------------------------------------------------------------------
    st.subheader('Suara TPS')
    st.write(f"""<p style="margin-top: -10px; margin-bottom: 25px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
    # --------------------------------------------------------------------------------------------------------------------------------------------------------------------
    a1, a2, a3, a4 = st.columns(4)
    # --------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Dropdown options PROVINSI
    opsi_prov = tps[tps.index.astype(str).str.len() == 2].sort_values('id2name')['id2name']
    nm_prov = a1.selectbox('Pilih Provinsi/Luar Negeri:', opsi_prov)
    id_prov = tps[(tps.index.astype(str).str.len() == 2) & (tps['id2name'] == nm_prov)].index[0]

    #Dropdown options KABUPATEN/KOTA
    opsi_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov)))].sort_values('id2name')['id2name']
    nm_kab = a2.selectbox('Pilih Kabupaten/Kota:', opsi_kab)
    id_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov))) & (tps['id2name'] == nm_kab)].index[0]

    #Dropdown options KECAMATAN
    opsi_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab)))].sort_values('id2name')['id2name']
    nm_kec = a3.selectbox('Pilih Kecamatan:', opsi_kec)
    id_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab))) & (tps['id2name'] == nm_kec)].index[0]

    #Dropdown options DESA/KELURAHAN
    opsi_desa = tps[(tps.index.astype(str).str.len() == 10) & (tps.index.astype(str).str.startswith(str(id_kec)))].sort_values('id2name')['id2name']
    nm_desa = a4.selectbox('Pilih Desa/Kelurahan:', opsi_desa)
    id_desa = tps[(tps.index.astype(str).str.len() == 10) & (tps.index.astype(str).str.startswith(str(id_kec))) & (tps['id2name'] == nm_desa)].index[0]
        
    id = id_desa   
    
    # ---------------------------------------------------------------------------------------------------------------------------------------
    c1, c2, c3 = st.columns([6,2,2])
    
    # ---------------------------------------------------------------------------------------------------------------------------------------
    # Filter
    # ---------------------------------------------------------------------------------------------------------------------------------------
    c1.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id)[0:2]),'id2name']} | 
                <b>  KAB/KOTA:</b> {tps.loc[int(str(id)[0:4]),'id2name']} |
                <b>  KECAMATAN:</b> {tps.loc[int(str(id)[0:6]),'id2name']} <br> 
                <b>  DESA/KELURAHAN:</b> {tps.loc[int(id),'id2name']} ({id_desa})
                """, unsafe_allow_html=True)
    
    # ---------------------------------------------------------------------------------------------------------------------------------------
    # URL untuk link tombol Kawal Pemilu & Sirekap KPU
    # ---------------------------------------------------------------------------------------------------------------------------------------      
    c2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(id), use_container_width = True)
    c3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(id)[0:2]+"/"+str(id)[0:4]+"/"+str(id)[0:6]+"/"+str(id), use_container_width = True)  

    # ---------------------------------------------------------------------------------------------------------------------------------------   
    id = int(id)  
    # ---------------------------------------------------------------------------------------------------------------------------------------   

    # Menampilkan dataframe
    df = compare(id, tingkat = 'kel')

    # ---------------------------------------------------------------------------------------------------------------------------------------
    # Hitung Jumlah TPS
    # ---------------------------------------------------------------------------------------------------------------------------------------
    # Menghitung total semua TPS
    total_tps = df['tps'].count()

    # Memformat total semua TPS dengan menambahkan koma sebagai pemisah ribuan
    total_tps_formatted = "{:,}".format(total_tps)    
    
    # ---------------------------------------------------------------------------------------------------------
    # 01
    # ---------------------------------------------------------------------------------------------------------
    # Menghitung total suara Sah
    total_pas1 = df['pas1_sirekap'].sum()

    # Memformat total suara Sah dengan menambahkan koma sebagai pemisah ribuan
    total_pas1_formatted = "{:,}".format(total_pas1)    

    # ---------------------------------------------------------------------------------------------------------
    # 02
    # ---------------------------------------------------------------------------------------------------------
    # Menghitung total suara Sah
    total_pas2 = df['pas2_sirekap'].sum()

    # Memformat total suara Sah dengan menambahkan koma sebagai pemisah ribuan
    total_pas2_formatted = "{:,}".format(total_pas2)
    
    # ---------------------------------------------------------------------------------------------------------
    # 03
    # ---------------------------------------------------------------------------------------------------------
    # Menghitung total suara Sah
    total_pas3 = df['pas3_sirekap'].sum()

    # Memformat total suara Sah dengan menambahkan koma sebagai pemisah ribuan
    total_pas3_formatted = "{:,}".format(total_pas3)    

    # ---------------------------------------------------------------------------------------------------------
    # Hitung Suara Sah
    # ---------------------------------------------------------------------------------------------------------
    # Menghitung total suara Sah
    total_sah = total_pas1+total_pas2+total_pas3

    # Memformat total suara Sah dengan menambahkan koma sebagai pemisah ribuan
    total_sah_formatted = "{:,}".format(total_sah)

    #persentase 01
    total_pas1_percent = (total_pas1 / total_sah) * 100

    #format persentase dengan 2 digit desimal
    total_pas1_percent_formatted = f"{total_pas1_percent:.2f}"

    #persentase 02
    total_pas2_percent = (total_pas2 / total_sah) * 100

    #format persentase dengan 2 digit desimal
    total_pas2_percent_formatted = f"{total_pas2_percent:.2f}"

    #persentase 03
    total_pas3_percent = (total_pas3 / total_sah) * 100

    #format persentase dengan 2 digit desimal
    total_pas3_percent_formatted = f"{total_pas3_percent:.2f}"

    
    st.write(f"""<p style="margin-top: 10px; margin-bottom: 10px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
    
    st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara di Desa/Kelurahan <b>{tps.loc[int(id),'id2name']} ({id_desa})</b> dengan Total Suara Sah sebanyak <b>{total_sah_formatted}</b>, dan TPS ada <b>{total_tps_formatted}</b></p>""", unsafe_allow_html=True)
    
    p1, p2, p3 = st.columns(3)

    with p1:
        st.header("01")
        p1a, p1b = st.columns([1,2])
        p1a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
        with p1b:               
            st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas1_formatted}</b> ({total_pas1_percent_formatted}%) </p>""", unsafe_allow_html=True)     
    
    with p2:
        st.header("02")
        p2a, p2b = st.columns([1,2])
        p2a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
        with p2b:
            st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas2_formatted}</b> ({total_pas2_percent_formatted}%) </p>""", unsafe_allow_html=True)
    
    with p3:
        st.header("03")
        p3a, p3b = st.columns([1,2])
        p3a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
        with p3b:
            st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas3_formatted}</b> ({total_pas3_percent_formatted}%) </p>""", unsafe_allow_html=True)
      
    st.dataframe(
        df.iloc[:30].style.apply(row_color, axis=1), 
        height=500,
        hide_index=True,
        use_container_width=True
    )
        
    #Menampilkan diagram batang
    st.subheader('📊 Diagram Suara:')
    c4, c5 = st.columns(2)
    # ---------------------------------------------------------------------------------------------------------------------------------------
    c4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
    c4.bar_chart(df[['tps','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'tps': 'no_tps'}), 
                x='no_tps',
                color=['#CCFFCC','#CCCCFF','#FFCCCC'])
    # ---------------------------------------------------------------------------------------------------------------------------------------
    c5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
    c5.bar_chart(df[['tps','pas1_sirekap','pas2_sirekap','pas3_sirekap']].rename(columns={'tps': 'no_tps'}), 
                x='no_tps', 
                color=['#CCFFCC','#CCCCFF','#FFCCCC']) 

# Per Wilayah
with tab3:   
    # ---------------------------------------------------------------------------------------------------------------------------------------
    st.subheader('Suara Wilayah')
    st.write(f"""<p style="margin-top: -10px; margin-bottom: 25px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
    # ---------------------------------------------------------------------------------------------------------------------------------------

    # ---------------------------------------------------------------------------------------------------------------------------------------
    d1, d2, d3 = st.columns(3)
    # ---------------------------------------------------------------------------------------------------------------------------------------

    #Dropdown options PROVINSI
    opsi_prov = tps[tps.index.astype(str).str.len() == 2]['id2name']
    nm_prov = d1.selectbox('Pilih Provinsi/Luar Negeri:', opsi_prov, key='d_prov')
    id_prov = tps[(tps.index.astype(str).str.len() == 2) & (tps['id2name'] == nm_prov)].index[0]

    #Dropdown options KABUPATEN/KOTA
    opsi_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov)))]['id2name']
    nm_kab = d2.selectbox('Pilih Kabupaten/Kota:', opsi_kab, key='d_kab')
    id_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov))) & (tps['id2name'] == nm_kab)].index[0]

    #Dropdown options KECAMATAN
    opsi_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab)))]['id2name']
    nm_kec = d3.selectbox('Pilih Kecamatan:', opsi_kec, key='d_kec')
    id_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab))) & (tps['id2name'] == nm_kec)].index[0]

    id_wil = id_kec

    tab_provinsi, tab_kabkot, tab_kecamatan = st.tabs(['Provinsi','Kabupaten/Kota','Kecamatan'])
    
    with tab_provinsi:
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.subheader('Per Provinsi:')
        # ---------------------------------------------------------------------------------------------------------------------------------------
        x1, x2, x3 = st.columns([6,2,2])                
        
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Filter
        # ---------------------------------------------------------------------------------------------------------------------------------------
        x1.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # URL untuk link tombol Kawal Pemilu & Sirekap KPU
        # ---------------------------------------------------------------------------------------------------------------------------------------      
        x2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(id_wil)[0:2], use_container_width = True)
        x3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(id_wil)[0:2], use_container_width = True)  

        # ---------------------------------------------------------------------------------------------------------------------------------------
        id = int(id_wil)

        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'prov')

       # Setelah mengurutkan DataFrame berdasarkan nama
        df_sorted_filtered = df.sort_values(by='name')

       # Atur ulang indeks DataFrame setelah pengurutan
        df_sorted_filtered = df_sorted_filtered.reset_index(drop=True)

       # Menambahkan kolom 'No'
        df.insert(0, 'No', df_sorted_filtered.index + 1)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total Kabupaten
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total Kabupaten
        total_kab = df['name'].count()

       # Memformat total Kabupaten dengan menambahkan koma sebagai pemisah ribuan
        total_kab_formatted = "{:,}".format(total_kab)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total TPS
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total jumlah TPS
        total_tps = df['totalTps'].sum()

        # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_formatted = "{:,}".format(total_tps)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Tampilkan
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara Provinsi <b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} </b>, di <b>{total_kab_formatted}</b> Kabupaten/Kota, dengan Total TPS <b> {total_tps_formatted} </b>. </p>""", unsafe_allow_html=True)
        st.dataframe(
            df.iloc[:230].style.apply(row_color, axis=1), 
            height=2100,         
            hide_index=True, 
            use_container_width=True
        )    
        
        #Menampilkan diagram batang
        st.subheader('📊 Diagram Suara:')
        x4, x5 = st.columns(2)
        # ---------------------------------------------------------------------------------------------
        x4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
        x4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kabupaten_kota'}), 
                    x='kabupaten_kota',
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        # ---------------------------------------------------------------------------------------------
        x5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
        x5.bar_chart(df[['name',
                        'pas1_sirekap',
                        'pas2_sirekap',
                        'pas3_sirekap']].rename(columns={'name': 'kabupaten_kota'}), 
                    x='kabupaten_kota', 
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])        
        
    with tab_kabkot:
        # -- ------------------------------------------------------------------------------------------------------------
        st.subheader('Per Kabupaten/Kota:')
        # --------------------------------------------------------------------------------------------------------------------------------------------
        y1, y2, y3 = st.columns([6,2,2])
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Filter
        # ---------------------------------------------------------------------------------------------------------------------------------------
        y1.write(f"""
                <b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} | 
                <b>  KABUPATEN/KOTA:</b> {tps.loc[int(str(id_wil)[0:4]),'id2name']}
                """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # URL untuk link tombol Kawal Pemilu & Sirekap KPU
        # ---------------------------------------------------------------------------------------------------------------------------------------      
        y2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(id_wil), use_container_width = True)
        y3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(id_wil)[0:2]+"/"+str(id_wil)[0:4], use_container_width = True)   

        # ---------------------------------------------------------------------------------------------------------------------------------------
        id = int(id_wil)
        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'kab')

       # Setelah mengurutkan DataFrame berdasarkan nama
        df_sorted_filtered = df.sort_values(by='name')

       # Atur ulang indeks DataFrame setelah pengurutan
        df_sorted_filtered = df_sorted_filtered.reset_index(drop=True)

       # Menambahkan kolom 'No'
        df.insert(0, 'No', df_sorted_filtered.index + 1)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Total TPS
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Menghitung total jumlah TPS
        total_tps = df['totalTps'].sum()

        # Memformat total jumlah TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_formatted = "{:,}".format(total_tps)

        st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara di Kabupaten/Kota <b> {tps.loc[int(str(id_wil)[0:4]),'id2name']} </b>, dengan Total TPS sebanyak <b> {total_tps_formatted} </b>. </p>""", unsafe_allow_html=True)
        st.dataframe(
            df.iloc[:230].style.apply(row_color, axis=1), 
            height=2100,          
            hide_index=True, 
            use_container_width=True
        )    
        
        #Menampilkan diagram batang
        st.subheader('📊 Diagram Suara:')
        y4, y5 = st.columns(2)
        # ----------------------------------------------------------------------------------------------------------------------------------------
        y4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
        y4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kecamatan'}), 
                    x='kecamatan',
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        # ----------------------------------------------------------------------------------------------------------------------------------------
        y5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
        y5.bar_chart(df[['name','pas1_sirekap','pas2_sirekap','pas3_sirekap']].rename(columns={'name': 'kecamatan'}), 
                    x='kecamatan', 
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])        
        
    with tab_kecamatan:
        # ---------------------------------------------------------------------------------------------------------------------------------------
        st.subheader('Per Kecamatan:')
        # ---------------------------------------------------------------------------------------------------------------------------------------
        z1, z2, z3 = st.columns([6,2,2])
        # ---------------------------------------------------------------------------------------------------------------------------------------
        # Filter
        # ---------------------------------------------------------------------------------------------------------------------------------------
        z1.write(f"""
                <b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} | 
                <b>  KAB/KOTA:</b> {tps.loc[int(str(id_wil)[0:4]),'id2name']} <br>
                <b>  KECAMATAN:</b> {tps.loc[int(str(id_wil)),'id2name']}
                """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------------------------------------------------------------
        # URL untuk link tombol Kawal Pemilu & Sirekap KPU
        # ---------------------------------------------------------------------------------------------------------------------------------------      
        z2.link_button("🧭 Kawal Pemilu", url_kawal_pemilu +str(id_wil), use_container_width = True)
        z3.link_button("📅 SIREKAP KPU", url_sirekap_sirekap +str(id_wil)[0:2]+"/"+str(id_wil)[0:4]+"/"+str(id_wil), use_container_width = True)       
        
        # ---------------------------------------------------------------------------------------------------------------------------------------
        id = int(id_wil)
        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'kec')

       # Setelah mengurutkan DataFrame berdasarkan nama
        df_sorted_filtered = df.sort_values(by='name')

       # Atur ulang indeks DataFrame setelah pengurutan
        df_sorted_filtered = df_sorted_filtered.reset_index(drop=True)

       # Menambahkan kolom 'No'
        df.insert(0, 'No', df_sorted_filtered.index + 1)

        # Menghitung total Suara Sah
        total_sah = df['sah_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_sah_formatted = "{:,}".format(total_sah)

        # Menghitung total semua TPS
        total_tps = df['totalTps'].sum()

        # Memformat total semua TPS dengan menambahkan koma sebagai pemisah ribuan
        total_tps_formatted = "{:,}".format(total_tps)
        
        st.write(f"""<p style="margin-top: 10px; margin-bottom: 10px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
        
        st.write(f"""<p style="margin-top: 15px; font-size: 16px;">Tabulasi: Perolehan Suara di Desa/Kelurahan <b>{tps.loc[int(id_wil),'id2name']}</b> dengan Total Suara Sah sebanyak <b>{total_sah_formatted}</b>, dan TPS ada <b>{total_tps_formatted}</b></p>""", unsafe_allow_html=True)
        
        # ---------------------------------------------------------------------------------------------------------
        # 01
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas1 = df['pas1_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas1_formatted = "{:,}".format(total_pas1)

        #persentase
        total_pas1_percent = (total_pas1 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas1_percent_formatted = f"{total_pas1_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 02
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas2 = df['pas2_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas2_formatted = "{:,}".format(total_pas2)

        #persentase
        total_pas2_percent = (total_pas2 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas2_percent_formatted = f"{total_pas2_percent:.2f}"

        # ---------------------------------------------------------------------------------------------------------
        # 03
        # ---------------------------------------------------------------------------------------------------------
        # Menghitung total Suara Sah
        total_pas3 = df['pas3_sirekap'].sum()

        # Memformat total Suara Sah dengan menambahkan koma sebagai pemisah ribuan
        total_pas3_formatted = "{:,}".format(total_pas3)

        #persentase
        total_pas3_percent = (total_pas3 / total_sah) * 100

        #format persentase dengan 2 digit desimal
        total_pas3_percent_formatted = f"{total_pas3_percent:.2f}"

        p1, p2, p3 = st.columns(3)

        with p1:
            st.header("01")
            p1a, p1b = st.columns([1,2])
            p1a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
            with p1b:               
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas1_formatted}</b> ({total_pas1_percent_formatted}%) </p>""", unsafe_allow_html=True)     
        
        with p2:
            st.header("02")
            p2a, p2b = st.columns([1,2])
            p2a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
            with p2b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas2_formatted}</b> ({total_pas2_percent_formatted}%) </p>""", unsafe_allow_html=True)
        
        with p3:
            st.header("03")
            p3a, p3b = st.columns([1,2])
            p3a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
            with p3b:
                st.write(f"""<p style="margin-top: -15px; font-size: 16px;"> 📣 Suara Sah : <b>{total_pas3_formatted}</b> ({total_pas3_percent_formatted}%) </p>""", unsafe_allow_html=True)

        st.dataframe(
            df.iloc[:30].style.apply(row_color, axis=1), 
            height=500,           
            hide_index=True, 
            use_container_width=True
        )    
        
        #Menampilkan diagram batang
        st.subheader('📊 Diagram Suara:')
        z4, z5 = st.columns(2)
        # ----------------------------------------------------------------------------------------------------------------------------------------
        z4.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_kawal_pemilu}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Kawal Pemilu </p>""", unsafe_allow_html=True)
        z4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'desa_kelurahan'}), 
                    x='desa_kelurahan',
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        # ---------------------------------------------------------------------------------------------------------------------------------------
        z5.markdown(f"""<p style="font-size: 18px;"><img src="{logo_url_sirekap_sirekap}" alt="Sirekap KPU" style="height: 45px; margin-right: 5px;"> Sirekap KPU </p>""", unsafe_allow_html=True)
        z5.bar_chart(df[['name','pas1_sirekap','pas2_sirekap','pas3_sirekap']].rename(columns={'name': 'desa_kelurahan'}), 
                    x='desa_kelurahan', 
                    color=['#CCFFCC','#CCCCFF','#FFCCCC'])  


# Paslon
with tab4:
    # ---------------------------------------------------------------------------------------------------------------------------------------
    st.subheader('Suara Paslon 2024')
    st.write(f"""<p style="margin-top: -10px; margin-bottom: 25px; border-bottom: 1px solid #e3e3e3"></p>""", unsafe_allow_html=True)
    # ---------------------------------------------------------------------------------------------------------------------------------------

    #Rekapitulasi Sirekap KPU
    kpu = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp.json").json()['chart']
    kpu_pas1 = kpu['100025']
    kpu_pas2 = kpu['100026']
    kpu_pas3 = kpu['100027']
    kpu_tot = kpu['100025'] + kpu['100026'] + kpu['100027']

    #Rekapitulasi Kawal Pemilu
    kawal = requests.get("https://kp24-fd486.et.r.appspot.com/h?id=").json()['result']['aggregated']
    kawal_pas1 = 0
    kawal_pas2 = 0
    kawal_pas3 = 0
    for lokasi in kawal.values():
        for entry in lokasi:
            kawal_pas1 += entry['pas1']
            kawal_pas2 += entry['pas2']
            kawal_pas3 += entry['pas3']
    kawal_tot = kawal_pas1 + kawal_pas2 + kawal_pas3
    
    c8, c9, c10 = st.columns(3)

    with c8:
        st.header("01")
        c8a, c8b = st.columns([4,2])
        c8a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
        with c8b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                    value=str(round((kpu_pas1/kpu_tot)*100,2))+'%', 
                    delta="{:,}".format(kpu_pas1),
                    delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                    value=str(round((kawal_pas1/kawal_tot)*100,2))+'%', 
                    delta="{:,}".format(kawal_pas1),
                    delta_color = 'off')
                
    
    with c9:
        st.header("02")
        c9a, c9b = st.columns([4,2])
        c9a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
        with c9b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                    value=str(round((kpu_pas2/kpu_tot)*100,2))+'%', 
                    delta="{:,}".format(kpu_pas2),
                    delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                    value=str(round((kawal_pas2/kawal_tot)*100,2))+'%', 
                    delta="{:,}".format(kawal_pas2),
                    delta_color = 'off')           
    
    with c10:
        st.header("03")
        c10a, c10b = st.columns([4,2])
        c10a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
        with c10b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                    value=str(round((kpu_pas3/kpu_tot)*100,2))+'%', 
                    delta="{:,}".format(kpu_pas3),
                    delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                    value=str(round((kawal_pas3/kawal_tot)*100,2))+'%', 
                    delta="{:,}".format(kawal_pas3),
                    delta_color = 'off')   
        
# -----------------------------------------------------------------------------------------------
#buat garis horizontal
# -----------------------------------------------------------------------------------------------
st.markdown("""---""")
st.write(f"""<p style="margin-top: -35px; font-size: 16px;"> <span style="float: left;" > 2024 ©. All rights reserved.</span> <span style="float: right;"> Developed by IT Data Riset and Development Surabaya - N124r.</span></p>""", unsafe_allow_html=True)