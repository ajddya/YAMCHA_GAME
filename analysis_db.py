import streamlit as st
import pandas as pd
import random
import os
from io import BytesIO
import shutil
import ast
import math
import unicodedata
import re
import uuid

button_css1 = f"""
    <style>
        div.stButton > button:first-child  {{
        color        : white               ;
        padding      : 14px 20px           ;
        margin       : 8px 0               ;
        width        : 100%                ;
        font-weight  : bold                ;/* 文字：太字                   */
        border       : 1px solid #000      ;/* 枠線：ピンク色で5ピクセルの実線 */
        border-radius: 1px 1px 1px 1px     ;/* 枠線：半径10ピクセルの角丸     */
        background   : #a9a9a9             ;/* 背景色：薄いグレー            */
    }}
    </style>
    """
st.markdown(button_css1, unsafe_allow_html=True)

def init():
    # sidebarのselectboxのpage_idを有効にするフラグ
    if "page_id_flag" not in st.session_state:
        st.session_state.page_id_flag = True
    
    # セッション状態にデータフレームがあるか確認
    if "df" not in st.session_state:
        st.session_state.df = None

    # データフレーム作成のデータフレーム
    if "create_df" not in st.session_state:
        st.session_state.create_df = None

    # 結合前の一時的なcreate_df
    if "create_df_temp" not in st.session_state:
        columns = ["🔴赤", "🔵青", "🟡黄", "🟢緑", "🟣紫"]
        st.session_state.create_df_temp = pd.DataFrame(columns=columns)

    if "player_df" not in st.session_state:
        st.session_state.player_df = pd.read_csv("player/player.csv")

    if "image_name" not in st.session_state:
        st.session_state.image_name = None

    if "uniform_role_flag" not in st.session_state:
        st.session_state.uniform_role_flag = False

    if "transition_flag" not in st.session_state:
        st.session_state.transition_flag = False

    if "output_decks" not in st.session_state:
        st.session_state.output_decks = []

    if "output_deck_num_default" not in st.session_state:
        st.session_state.output_deck_num_default = 1

    if "player_num_default" not in st.session_state:
        st.session_state.player_num_default = 1


# 文字コードを正規化
def normalize_text(text):
    return unicodedata.normalize('NFKC', str(text)).strip()

# データフレームを正規化
def normalize_dataframe(df):
    df_copy = df.copy()
    for col in df_copy.columns:
        df_copy[col] = df_copy[col].apply(lambda x: normalize_text(x) if pd.notna(x) else x)
    return df_copy

def normalize_filename(filename):
    return unicodedata.normalize('NFKC', filename)

def normalize_image_filenames(image_root="image"):
    color_folders = ["赤", "青", "緑", "黄", "紫"]
    for color in color_folders:
        folder_path = os.path.join(image_root, color)
        if not os.path.exists(folder_path):
            continue

        for filename in os.listdir(folder_path):
            normalized_name = normalize_filename(filename)

            if filename != normalized_name:
                old_path = os.path.join(folder_path, filename)
                # 一時ファイル名で確実に回避
                temp_name = f"__temp__{uuid.uuid4().hex}.tmp"
                temp_path = os.path.join(folder_path, temp_name)
                new_path = os.path.join(folder_path, normalized_name)

                # ① 一度仮名にリネーム（同一名衝突回避のため）
                os.rename(old_path, temp_path)

                # ② 正規化された名前にリネーム
                os.rename(temp_path, new_path)

# --- 🔽 各列をあいうえお順に並べ替え ---
# 各列をソートしてから、NaNで埋めて長さを揃える
def sort_df(df, columns = ["🔴赤", "🔵青", "🟡黄", "🟢緑", "🟣紫"]):
    
    sort_df = pd.DataFrame(columns=columns)

    max_len = 0
    sorted_columns = {}

    for col in columns:
        sorted_values = sorted(df[col].dropna())  # NaNを除いてソート
        sorted_columns[col] = sorted_values
        max_len = max(max_len, len(sorted_values))

    # ソート済みの値で新しいDataFrameを作成
    sorted_df = pd.DataFrame({
        col: sorted_columns[col] + [None] * (max_len - len(sorted_columns[col]))
        for col in columns
    })

    return sorted_df

#  指定されたフォルダ内のすべての.pngファイル名をリストで返す関数。    
def list_png_files(folder_path):
    try:
        # 指定フォルダ内のファイル一覧を取得し、.pngファイルだけを抽出
        png_files = [f for f in os.listdir(folder_path) if f.endswith(".png")]
        return png_files
    except FileNotFoundError:
        print(f"フォルダが見つかりません: {folder_path}")
        return []
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return []

# deck_listフォルダからcsvファイル名一覧を表示・選択する
def select_csv_from_list_folder():
    folder_path = "Deck_List"

    # listフォルダ内のcsvファイルを取得
    try:
        csv_files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]
    except FileNotFoundError:
        st.error(f"フォルダが見つかりません: {folder_path}")
        return None

    if not csv_files:
        st.warning("Deck_List フォルダに CSV ファイルが見つかりませんでした。")
        return None

    # セッションに保存されたファイル名を初期値に設定
    default_index = 0
    if "filename" in st.session_state:
        default_file = os.path.basename(st.session_state.filename)
        if default_file in csv_files:
            default_index = csv_files.index(default_file)

    # selectboxで選択（初期値を設定）
    selected_csv = st.selectbox("CSVファイルを選択してください", csv_files, index=default_index)
    st.session_state.filename = selected_csv

    return os.path.join(folder_path, selected_csv)

# dfからタイトルを全て抽出する
def extract_unique_titles(df):
    titles = set()

    # 各列をループしてすべてのセルを処理
    for col in df.columns:
        for cell in df[col].dropna():
            match = re.match(r"^(.*?)\(", cell)
            if match:
                titles.add(match.group(1))

    return sorted(titles)

def extract_elements_by_title(df, target_title):
    matched_elements = []

    for col in df.columns:
        for cell in df[col].dropna():
            if cell.startswith(f"{target_title}("):
                matched_elements.append(cell)

    return matched_elements

# dfをTierで並べ替え
def df_to_tier_df(df):
    # Tier の分類リスト（必要に応じて変更）
    tier_list = ["Tier1.0", "Tier1.5", "Tier2.0", "Tier2.5", "Tier3.0", "Tier4.0", "Tier5.0"]
    tier_df = pd.DataFrame(columns=tier_list)

    for col in df.columns:
        for val in df[col]:
            if pd.notna(val):
                tier_num = Tier_of_Deck(val)
                tier = "Tier" + str(tier_num)
                if tier in tier_list:
                    tier_df = save_image_names_to_df(tier_df, tier, val)
                else:
                    st.warning(f"Tierが無効または未定義です: {val} → {tier}")

    tier_df = sort_df(tier_df, tier_list)

    return tier_df

# dfからランダムに1要素を抽出
def get_random(df):
    # ランダムに1つのセル（要素）を取得（値がNoneでないもの）
    while True:
        row_idx = random.randint(0, len(df) - 1)
        col_idx = random.randint(0, len(df.columns) - 1)
        random_value = df.iat[row_idx, col_idx]
        if pd.notna(random_value):  # 選択された要素は NaN ではない
            break
        
    return random_value

# new_player_list を player にコピーする
def save_csv():
    # 新しいデータベースファイルのパス
    new_csv_path = 'player/new_player_list.csv'

    # 置き換える既存のデータベースファイルのパス
    existing_csv_path = 'player/player.csv'

    # 新しいファイルが存在するか確認
    if os.path.exists(new_csv_path):
        # 新しいデータベースファイルで既存のファイルを置き換え
        shutil.copyfile(new_csv_path, existing_csv_path)

    else:
        st.sidebar.write("データの保存に失敗しました。")

# デッキ名からTierを出力する
def Tier_of_Deck(deck_name):
    # listフォルダ内のcsvファイルを取得
    try:
        Tier_df_red = pd.read_csv("Tier_List/Tier_List_赤.csv")
        Tier_df_bulue = pd.read_csv("Tier_List/Tier_List_青.csv")
        Tier_df_green = pd.read_csv("Tier_List/Tier_List_緑.csv")
        Tier_df_yellow = pd.read_csv("Tier_List/Tier_List_黄.csv")
        Tier_df_purple = pd.read_csv("Tier_List/Tier_List_紫.csv")
        Tier_df = pd.concat(
            [Tier_df_red, Tier_df_bulue, Tier_df_green, Tier_df_yellow, Tier_df_purple],
            ignore_index=True
        )
    except FileNotFoundError:
        st.error(f"フォルダが見つかりません: {folder_path}")
        return None    

    # deck_name を正規化
    normalized_deck_name = normalize_text(deck_name)

    # データフレーム内のデッキ名もすべて正規化
    Tier_df["デッキ名_正規化"] = Tier_df["デッキ名"].map(normalize_text)

    try:
        Tier_num = Tier_df[Tier_df["デッキ名_正規化"] == normalized_deck_name]["Tier"].values[0]
    except IndexError:
        st.error("デッキ名がTier_Listに登録されていません")
        return None

    return Tier_num

# my_deck_listからTier平均を出力
def Avg_Tier_of_Deck(selected_player):
    # image_namesを取得（安全に抽出）
    try:
        image_names_raw = st.session_state.player_df[
            st.session_state.player_df["名前"] == selected_player
        ]["image_names"].values[0]
    except IndexError:
        st.warning("プレイヤーデータが見つかりません。")
        return None

    image_list = ast.literal_eval(image_names_raw) if isinstance(image_names_raw, str) else image_names_raw

    if not isinstance(image_list, list) or len(image_list) == 0:
        st.warning("デッキが登録されていません。")
        return None

    # 各デッキのTierを取得し、平均を計算
    tier_values = []
    for image_name in image_list:
        deck_name = image_name.replace(".png", "")
        tier = Tier_of_Deck(deck_name)
        if tier is not None:
            tier_values.append(tier)

    if not tier_values:
        st.warning("Tier情報が取得できませんでした。")
        return None

    avg_tier = sum(tier_values) / len(tier_values)
    truncated_avg = math.floor(avg_tier * 100) / 100  # 小数第2位で切り捨て

    return truncated_avg

# player毎にimage_nameのリストを格納
def save_image_names(player, image_name):
    # プレイヤーの行インデックスを取得
    player_idx = st.session_state.player_df[st.session_state.player_df["名前"] == player].index[0]

    # 現在の画像リストを取得（空なら空リスト）
    current_images = st.session_state.player_df.at[player_idx, "image_names"]
    
    if pd.isna(current_images) or current_images == "":
        image_list = []
    else:
        try:
            image_list = ast.literal_eval(current_images)
        except (ValueError, SyntaxError):
            st.warning("画像リストの読み取りに失敗しました。新しく初期化します。")
            image_list = []

    # 重複しないように追加
    if image_name in image_list:
        st.warning("この画像はすでに追加されています。")
    else:
        image_list.append(image_name)
        st.session_state.player_df.at[player_idx, "image_names"] = str(image_list)
        st.session_state.player_df.to_csv("player/new_player_list.csv", index=False)
        st.success(f"{image_name} を {player} に追加しました！")

# dfにimage_nameを格納
def save_image_names_to_df(df, selected_column, image_name):

    deck_name = image_name.replace(".png", "")

    # すでに同じdeck_nameが列に存在する場合は警告を表示
    if deck_name in df[selected_column].values:
        st.warning(f"警告: `{deck_name}` はすでに列 `{selected_column}` に存在します。")

    # 指定された列にNaNがある場合、そのNaNをdeck_nameで埋める
    elif df[selected_column].isna().any():  # NaNが1つでもあるか確認
        # 最初のNaNを見つけてdeck_nameを代入
        nan_index = df[df[selected_column].isna()].index[0]
        df.at[nan_index, selected_column] = deck_name
    else:
        # NaNがなければ、新しい行を追加してdeck_nameを挿入
        new_row = {col: None for col in df.columns}  # 既存列名に対してNoneの辞書を作成
        new_row[selected_column] = deck_name  # 指定された列にデッキ名を挿入
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    return df

# df1とdf2を結合（df1にdf2をマージ）
def merge_dfs_with_function(df1, df2):
    df1_normalized = normalize_dataframe(df1)
    df2_normalized = normalize_dataframe(df2)

    merged_df = df1_normalized.copy()

    for col in df2_normalized.columns:
        for val in df2_normalized[col].dropna():
            image_name = str(val) + ".png" if not str(val).endswith(".png") else str(val)
            merged_df = save_image_names_to_df(merged_df, col, image_name)

    return merged_df

# 名前から画像を表示する
def output_image(df, image_name):

    image_path_red = os.path.join("image/赤", image_name)
    image_path_bulue = os.path.join("image/青", image_name)
    image_path_green = os.path.join("image/緑", image_name)
    image_path_yellow = os.path.join("image/黄", image_name)
    image_path_purple = os.path.join("image/紫", image_name)

    target_value = normalize_text(image_name.replace(".png", ""))
    found = False
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = df.iat[row_idx, col_idx]
            if pd.notna(cell_value) and normalize_text(cell_value) == target_value:
                col_name = df.columns[col_idx]
                st.write(f"{target_value}")
                found = True
                break
        if found:
            break

    if os.path.exists(image_path_red):
        st.image(image_path_red, width=150, use_container_width=False)
        st.subheader(f"Tier : {Tier_of_Deck(target_value)}")
    elif os.path.exists(image_path_bulue):
        st.image(image_path_bulue, width=150, use_container_width=False)
        st.subheader(f"Tier : {Tier_of_Deck(target_value)}")
    elif os.path.exists(image_path_green):
        st.image(image_path_green, width=150, use_container_width=False)
        st.subheader(f"Tier : {Tier_of_Deck(target_value)}")
    elif os.path.exists(image_path_yellow):
        st.image(image_path_yellow, width=150, use_container_width=False)
        st.subheader(f"Tier : {Tier_of_Deck(target_value)}")
    elif os.path.exists(image_path_purple):
        st.image(image_path_purple, width=150, use_container_width=False)
        st.subheader(f"Tier : {Tier_of_Deck(target_value)}")
    else:
        st.error(f"画像ファイルが見つかりません")

# データフレームの要素を3列で全て表示(selectboxで列を指定して表示)
def three_way_output_image(df, selected_column=None, selected_title=None, selected_player=None, selected_df=None):

    if selected_column is not None:
        # NaNを除いて値を取得し、.pngを付与
        image_names = df[selected_column].dropna().astype(str).tolist()
        image_names = [name + ".png" if not name.endswith(".png") else name for name in image_names]
        if image_names == []:
            st.header("該当条件を満たすデッキはありません")

    if selected_title is not None:
        image_names = selected_title
        image_names = [name + ".png" if not name.endswith(".png") else name for name in image_names]

    # 画像を3つずつ横並びで表示
    for i in range(0, len(image_names), 3):
        cols = st.columns(3)
        for j, image_name in enumerate(image_names[i:i+3]):
            with cols[j]:
                output_image(df, image_name)
                if selected_player is not None:
                    if st.button(f'{selected_player}に登録',key=f"image_{i}_{j}"):
                        save_image_names(selected_player, image_name)
                elif selected_df is not None:
                    if st.button('データフレームに登録',key=f"image_{i}_{j}"):
                        if selected_title is not None:
                            # image_nameからselected_solumnを作成
                            deck_name = image_name.replace(".png", "")
                            selected_column = next((col for col in selected_df.columns 
                                if deck_name in selected_df[col].values), None)

                        if selected_column in ["Tier1.0", "Tier1.5", "Tier2.0", "Tier2.5", "Tier3.0", "Tier4.0", "Tier5.0"]:
                            if "create_df_temp2" in st.session_state and not st.session_state.create_df_temp2.empty:
                                # selected_columnをTier_numから色に変える
                                deck_name = image_name.replace(".png", "")
                                for col in st.session_state.create_df_temp2.columns:
                                    if deck_name in st.session_state.create_df_temp2[col].values:
                                        selected_column = col
                                        break
                            
                        # selected_dfにデッキを登録
                        st.session_state.create_df_temp = save_image_names_to_df(st.session_state.create_df_temp, selected_column, image_name)     
        st.write("_____________________________________________________________")              

# 指定プレイヤーの image_names から特定の image_name を削除する関数
def remove_image_name(player, image_name):
    # プレイヤーの行インデックスを取得
    player_idx = st.session_state.player_df[st.session_state.player_df["名前"] == player].index[0]

    # 現在の画像リストを取得（空なら空リスト）
    current_images = st.session_state.player_df.at[player_idx, "image_names"]

    if pd.isna(current_images) or current_images == "":
        st.warning("画像リストは空です。削除できる画像がありません。")
        return
    else:
        try:
            image_list = ast.literal_eval(current_images)
        except (ValueError, SyntaxError):
            st.error("画像リストの読み取りに失敗しました。")
            return

    # 画像がリストにある場合のみ削除
    if image_name in image_list:
        image_list.remove(image_name)
        st.session_state.player_df.at[player_idx, "image_names"] = str(image_list)
        st.session_state.player_df.to_csv("player/new_player_list.csv", index=False)
        st.success(f"{image_name} を {player} から削除しました！")
    else:
        st.warning("指定された画像はリストに存在しません。")
    
# ダウンロード用の関数
def download_dataframe_as_csv(filename: str, df: pd.DataFrame):
    if df is not None and not df.empty:
        # ファイル名に .csv を強制的に付ける
        if not filename.endswith(".csv"):
            filename += ".csv"

        # データをCSV形式にエンコード（バイトIOで）
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        # ダウンロードボタン
        st.download_button(
            label="CSVファイルをダウンロード",
            data=buffer,
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.warning("ダウンロードするデータがありません。")

#_________________________________________________________________________________________________________________

def home_screen():
    st.header("やむちゃゲーム　〜ユニオンアリーナ〜")

    image_path = os.path.join("ホーム画面", "ホーム画面.png")
    st.image(image_path)

    if st.button("スタート"):
        st.session_state.page_id = "データベース選択"
        st.rerun()

def csv_app():
    st.title('ファイル選択')


    st.write("_____________________________________________________________")
    # ファイルアップロード
    uploaded_file = st.file_uploader("CSVデータベースファイルをアップロードしてください", type="csv")
    
    st.write("_____________________________________________________________")

    if uploaded_file is not None:
        # CSVをデータフレームとして読み込む
        df = pd.read_csv(uploaded_file)
        df = normalize_dataframe(df)
        df = sort_df(df)
        st.session_state.df = df  # セッションに保存
        st.session_state.filename = uploaded_file.name  # ファイル名も保存
    else:
        selected_csv_path = select_csv_from_list_folder()
        if selected_csv_path:
            df = pd.read_csv(selected_csv_path)
            df = normalize_dataframe(df)
            df = sort_df(df)
            st.session_state.df = df
            st.session_state.filename = os.path.basename(selected_csv_path)

    # セッションにデータがあるか安全に確認
    if "df" in st.session_state and st.session_state.df is not None:
        st.write(f"アップロードされたファイル名: `{st.session_state.filename}`")
        check_box = st.checkbox("アップロードファイルを表示")
        if check_box:
            st.dataframe(st.session_state.df)
            tier_values = []

            for col in st.session_state.df.columns:
                for val in st.session_state.df[col]:
                    if pd.notna(val):
                        tier_num = Tier_of_Deck(val)
                        if tier_num is not None:
                            tier_values.append(tier_num)

            if tier_values:
                average_tier = sum(tier_values) / len(tier_values)
                st.write(f"総デッキ数: {len(tier_values)}")
                st.write(f"平均Tier: {average_tier:.2f}")

    else:
        st.info("CSVファイルをアップロードしてください。")

    st.write("_____________________________________________________________")
    if st.button("データベース作成"):
        st.session_state.page_id_flag = False
        st.session_state.page_id = "データベース作成"
        # rerun前に必要なセッションキーが揃っていることを保証
        st.rerun()
        
def create_csv():
    st.title("データベース作成")
    st.write("_____________________________________________________________")
    if st.button("2つのアップロードファイルを結合して作成"):
        st.session_state.page_id = "データベース作成_1"
        st.rerun()

    if st.button("1つのアップロードファイルにデッキを追加して作成"):
        st.session_state.page_id = "データベース作成_2"
        st.rerun()

    if st.button("最初からファイルを作成"):
        st.session_state.page_id = "データベース作成_3_1"
        st.rerun()
    st.write("_____________________________________________________________")
    st.write("作成したデータベースを確認　＆　ダウンロード")

    if st.session_state.create_df is not None:
        st.subheader("作成したデータベース")
        st.dataframe(st.session_state.create_df)

        # ファイル名をユーザーに入力してもらう
        file_name_input = st.text_input("保存するCSVファイル名を入力してください")
        if file_name_input != "":
            download_dataframe_as_csv(file_name_input, st.session_state.create_df)

    st.write("_____________________________________________________________")
    if st.button("戻る"):
        st.session_state.page_id = "データベース選択"
        st.session_state.page_id_flag = True
        st.rerun()

# 2つのアップロードファイルを結合して作成
def create_csv_1():
    st.title("2つのアップロードファイルを結合して作成")

    uploaded_file_1 = st.file_uploader("CSVファイル_１をアップロードしてください", type="csv",key="file1")
    uploaded_file_2 = st.file_uploader("CSVファイル_２をアップロードしてください", type="csv",key="file2")

    df1 = df2 = None

    if uploaded_file_1:
        try:
            df1 = pd.read_csv(uploaded_file_1)
        except Exception as e:
            st.error(f"ファイル1の読み込みエラー: {e}")
    else:
        st.info("CSVファイル_1をアップロードしてください。")

    if uploaded_file_2:
        try:
            df2 = pd.read_csv(uploaded_file_2)
        except Exception as e:
            st.error(f"ファイル2の読み込みエラー: {e}")
    else:
        st.info("CSVファイル_2をアップロードしてください。")

    st.write("_____________________________________________________________")

    # 表示選択
    if df1 is not None and df2 is not None:
        selected_file = st.selectbox("表示するファイルを選択してください", ("CSVファイル_1", "CSVファイル_2"))

        if selected_file == "CSVファイル_1":
            st.subheader("CSVファイル_1 の内容")
            st.dataframe(df1)
        else:
            st.subheader("CSVファイル_2 の内容")
            st.dataframe(df2)

        if st.button("２つのCSVファイルを結合"):
            # 結合と保存
            combined_df = merge_dfs_with_function(df1, df2)
            st.session_state.combined_df = combined_df  # 一時的に保存
            st.subheader("結合されたデータフレーム")
            st.dataframe(combined_df)

        if "combined_df" in st.session_state:
            if st.button("CSVとして保存"):
                st.session_state.create_df = st.session_state.combined_df
                st.success("アップロードファイルとして保存しました")

    elif df1 is not None:
        st.subheader("CSVファイル_1 の内容")
        st.dataframe(df1)

    elif df2 is not None:
        st.subheader("CSVファイル_2 の内容")
        st.dataframe(df2)
    else:
        st.info("CSVファイルを1つ以上アップロードしてください。")


    st.write("_____________________________________________________________")
    if st.button("戻る"):
        st.session_state.page_id = "データベース作成"
        st.rerun()

# 1つのアップロードファイルにデッキを追加して作成
def create_csv_2():
    st.title("1つのアップロードファイルにデッキを追加して作成")

    uploaded_file = st.file_uploader("CSVファイル_１をアップロードしてください", type="csv")

    df1 = None

    if uploaded_file:
        try:
            df1 = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"ファイル1の読み込みエラー: {e}")
    else:
        st.info("CSVファイルをアップロードしてください。")

    if df1 is not None:
        check_box = st.checkbox("アップロードファイルを表示")
        if check_box:
            st.dataframe(df1)

    ################### create_csv_3を再利用 #######################
    if st.button("デッキ一覧表示"):
        st.session_state.transition_flag = True
        st.session_state.page_id = "データベース作成_3_1"
        st.rerun()
    ##############################################################

    if not st.session_state.create_df_temp.empty:
        check_box_2 = st.checkbox("作成ファイルを表示")
        if check_box_2:
            st.dataframe(st.session_state.create_df_temp)

    if df1 is not None and not st.session_state.create_df_temp.empty:
        st.write("_____________________________________________________________")
        if st.button("２つのCSVファイルを結合"):
            # 結合と保存
            combined_df = merge_dfs_with_function(df1, st.session_state.create_df_temp)
            st.session_state.combined_df = combined_df  # 一時的に保存
            st.subheader("結合されたデータフレーム")
            st.dataframe(combined_df)

        if "combined_df" in st.session_state:
            if st.button("CSVとして保存"):
                st.session_state.create_df = st.session_state.combined_df
                st.success("アップロードファイルとして保存しました")

    st.write("_____________________________________________________________")
    if st.button("戻る"):
        st.session_state.page_id = "データベース作成"
        st.rerun()

# 色からファイルを作成
def create_csv_3_1():
    st.title("最初からデッキを選択")
    # フラグによって戻り先を制御
    if st.session_state.transition_flag:
        if st.sidebar.button("戻る"):
            st.session_state.transition_flag = False
            st.session_state.page_id = "データベース作成_2"
            st.rerun()
    else:
        if st.sidebar.button("データベース作成画面に戻る"):
            st.session_state.page_id = "データベース作成"
            st.rerun()
    st.sidebar.write("______________________________________")
    
    ##################### subheader #####################

    if "create_df_temp2" not in st.session_state:
        columns = ["🔴赤", "🔵青", "🟡黄", "🟢緑", "🟣紫"]
        create_df_temp2 = pd.DataFrame(columns=columns)
        # 赤のpngファイル名を全て抽出
        png_files1 = list_png_files("image/赤")
        for file1 in png_files1:
            target_value1 = file1.replace(".png", "")
            create_df_temp2 = save_image_names_to_df(create_df_temp2,"🔴赤",target_value1)

        # 青のpngファイル名を全て抽出
        png_files2 = list_png_files("image/青")
        for file2 in png_files2:
            target_value2 = file2.replace(".png", "")
            create_df_temp2 = save_image_names_to_df(create_df_temp2,"🔵青",target_value2)

        # 緑のpngファイル名を全て抽出
        png_files3 = list_png_files("image/緑")
        for file3 in png_files3:
            target_value3 = file3.replace(".png", "")
            create_df_temp2 = save_image_names_to_df(create_df_temp2,"🟢緑",target_value3)

        # 黄のpngファイル名を全て抽出
        png_files4 = list_png_files("image/黄")
        for file4 in png_files4:
            target_value4 = file4.replace(".png", "")
            create_df_temp2 = save_image_names_to_df(create_df_temp2,"🟡黄",target_value4)

        # 紫のpngファイル名を全て抽出
        png_files5 = list_png_files("image/紫")
        for file5 in png_files5:
            target_value5 = file5.replace(".png", "")
            create_df_temp2 = save_image_names_to_df(create_df_temp2,"🟣紫",target_value5)

        # 保存 & 表示
        st.session_state.create_df_temp2 = sort_df(create_df_temp2)

    # Tier別dfを作成
    st.session_state.Tier_df = df_to_tier_df(st.session_state.create_df_temp2)

    select_method = st.radio("一覧表示方式を選択してください", ["色別", "タイトル別", "Tier別"], horizontal=True)

    if select_method == "色別":
        if "create_df_temp2" in st.session_state and not st.session_state.create_df_temp2.empty:
            # 列名を取得してセレクトボックスで表示
            selected_column = st.selectbox(
                "列を選択してください",
                options=st.session_state.create_df_temp2.columns.tolist()
            )
            
            # 選択された列名を表示（任意）
            st.write(f"選択された列: {selected_column}")

            selected_player=None
            selected_title=None
            three_way_output_image(st.session_state.create_df_temp2, selected_column, selected_title, selected_player, st.session_state.create_df_temp2)
        else:
            st.warning("データフレームが存在しないか空です。")

    elif select_method == "タイトル別":
        if "create_df_temp2" in st.session_state and not st.session_state.create_df_temp2.empty:
            # 列名を取得してセレクトボックスで表示
            unique_titles = extract_unique_titles(st.session_state.create_df_temp2)
            st.write("抽出された作品名一覧（あいうえお順）:")

            selected_title = st.selectbox("タイトル選択", unique_titles)

            results = extract_elements_by_title(st.session_state.create_df_temp2, selected_title)
            
            # 選択された列名を表示（任意）
            st.write(f"選択されたタイトル: {selected_title}")
            
            selected_player=None
            selected_column=None
            three_way_output_image(st.session_state.create_df_temp2, selected_column, results,selected_player, st.session_state.create_df_temp2)
        else:
            st.warning("データフレームが存在しないか空です。")

    elif select_method == "Tier別":
        # DataFrameが st.session_state に存在するか確認
        if "Tier_df" in st.session_state and not st.session_state.Tier_df.empty:
            tier_list = ["Tier1.0", "Tier1.5", "Tier2.0", "Tier2.5", "Tier3.0", "Tier4.0", "Tier5.0"]

            # 列名を取得してセレクトボックスで表示
            selected_column = st.selectbox(
                "列を選択してください",
                tier_list
            )
            
            # 選択された列名を表示（任意）
            st.write(f"選択された列: {selected_column}")

            selected_player=None
            selected_title=None
            three_way_output_image(st.session_state.Tier_df, selected_column, selected_title, selected_player, st.session_state.Tier_df)
        else:
            st.warning("データフレームが存在しないか空です。")

    if st.sidebar.button("CSVとして保存"):
        st.session_state.create_df = st.session_state.create_df_temp
        st.sidebar.success("アップロードファイルとして保存しました")

    st.sidebar.dataframe(st.session_state.create_df_temp)
    # 作成したデータフレーム確認
    for col in st.session_state.create_df_temp.columns:
        st.sidebar.write(f"{col} ")
        st.sidebar.write(st.session_state.create_df_temp[col].dropna().tolist())


def random_app():
    st.title("ランダム抽出")

    if st.session_state.df is not None:
        st.write(f"選択されているファイル: `{st.session_state.filename}`")
        check_box = st.checkbox("アップロードファイルを表示")
        if check_box:
            st.dataframe(st.session_state.df)   # データフレームを表示

        st.write("_____________________________________________________________")

        # 名前の選択ボックス
        selected_player = st.selectbox(
            label="プレイヤーを選択してください",
            options=st.session_state.player_df["名前"]
        )
        # 選択したプレイヤーの平均Tier
        avg_tier = Avg_Tier_of_Deck(selected_player)

        # 選んだ名前の表示
        st.write(f"選択されたプレイヤー: {selected_player}")
        st.write(f"プレイヤーの平均Tier: {avg_tier}")

        st.write("_____________________________________________________________")

        # 均一ルールをオンにチェックボックス
        st.session_state.uniform_role_flag = st.checkbox("均一ルール")
        # ランダムで出力するデッキ数を選択
        random_deck_num = st.slider("出力するデッキ数", 1, 10, st.session_state.output_deck_num_default)
        # スライダーのデフォルトを設定
        st.session_state.output_deck_num_default = random_deck_num

        # ランダム関数を使ってDFから１つ選択する。内容がNoneなら再度実施する
        # ボタンを押したらランダム抽出
        if st.button("ランダム抽出"):
            st.session_state.output_decks = []

            for _ in range(random_deck_num):

                if st.session_state.output_decks != []:
                    player_decks = st.session_state.player_df[st.session_state.player_df["名前"] == selected_player]["image_names"].values[0]
                    if not pd.isna(player_decks):
                        # player_decksをstrからリスト形式に
                        player_decks = re.findall(r"\['(.*?)'\]", player_decks)
                        player_decks_temp = []
                        for deck in player_decks:
                            deck_name = deck.replace(".png", "")
                            player_decks_temp.append(deck_name)
                        # シングルクォートとカンマで分割
                        player_decks_temp = [player_decks_temp.strip(" '") for player_decks_temp in player_decks_temp[0].split(",")]
                        deck_list_temp = st.session_state.output_decks + player_decks_temp
                    else:
                        deck_list_temp = st.session_state.output_decks
                        
                    sum_tier_temp = 0
                    for i in range(0, len(deck_list_temp)):
                        sum_tier_temp += Tier_of_Deck(deck_list_temp[i])

                    avg_tier_temp = sum_tier_temp / len(deck_list_temp)
                else:
                    deck_list_temp = []
                    avg_tier_temp = avg_tier

                if st.session_state.uniform_role_flag and avg_tier_temp is not None:
                    while True:
                        random_value = get_random(st.session_state.df)
                        # 重複してたらもう一度実行する
                        if random_value not in deck_list_temp:
                            deck_tier = Tier_of_Deck(random_value)
                            if avg_tier_temp < 2.7:
                                if deck_tier > 2.7:
                                    break
                            else:
                                if deck_tier < 2.7:
                                    break
                else:
                    while True:
                        random_value = get_random(st.session_state.df)
                        # 重複してたらもう一度実行する
                        if random_value not in deck_list_temp:
                            break

                st.session_state.output_decks.append(random_value)

        # 画像表示（選ばれていれば常に表示）
        if st.session_state.output_decks != []:
            # 画像を3つずつ横並びで表示
            for i in range(0, len(st.session_state.output_decks), 3):
                cols = st.columns(3)
                for j, image_name in enumerate(st.session_state.output_decks[i:i+3]):
                    with cols[j]:
                        output_image_name = image_name + ".png"
                        output_image(st.session_state.df, output_image_name)

            if st.button(f'{selected_player}にこのデッキを登録する'):
                for i in range(0, len(st.session_state.output_decks)):
                    output_image_name = st.session_state.output_decks[i] + ".png"
                    save_image_names(selected_player, output_image_name)


def customize():
    st.title('デッキリストカスタマイズ')
    st.write("_____________________________________________________________")

    # 名前の選択ボックス
    selected_player = st.selectbox(
        label="プレイヤーを選択してください",
        options=st.session_state.player_df["名前"]
    )
    # 選んだ名前の表示
    st.write(f"選択されたプレイヤー: {selected_player}")
    st.write("_____________________________________________________________")

    select_method = st.radio("一覧表示方式を選択してください", ["色別", "タイトル別", "Tier別"], horizontal=True)

    if select_method == "色別":
        # DataFrameが st.session_state に存在するか確認
        if "df" in st.session_state and not st.session_state.df.empty:
            # 列名を取得してセレクトボックスで表示
            selected_column = st.selectbox(
                "列を選択してください",
                options=st.session_state.df.columns.tolist()
            )
            
            # 選択された列名を表示（任意）
            st.write(f"選択された列: {selected_column}")

            selected_title = None
            three_way_output_image(st.session_state.df, selected_column, selected_title, selected_player)
        else:
            st.warning("データフレームが存在しないか空です。")

    elif select_method == "タイトル別":
        if "df" in st.session_state and not st.session_state.df.empty:
            # 列名を取得してセレクトボックスで表示
            unique_titles = extract_unique_titles(st.session_state.df)

            selected_title = st.selectbox("タイトル選択", unique_titles)

            results = extract_elements_by_title(st.session_state.df, selected_title)
            
            # 選択された列名を表示（任意）
            st.write(f"選択されたタイトル: {selected_title}")
            
            selected_column=None
            three_way_output_image(st.session_state.df, selected_column, results, selected_player)
        else:
            st.warning("データフレームが存在しないか空です。")

    elif select_method == "Tier別":
        st.session_state.Tier_df = df_to_tier_df(st.session_state.df)

        # DataFrameが st.session_state に存在するか確認
        if "Tier_df" in st.session_state and not st.session_state.Tier_df.empty:
            tier_list = ["Tier1.0", "Tier1.5", "Tier2.0", "Tier2.5", "Tier3.0", "Tier4.0", "Tier5.0"]

            # 列名を取得してセレクトボックスで表示
            selected_column = st.selectbox(
                "列を選択してください",
                tier_list
            )
            
            # 選択された列名を表示（任意）
            st.write(f"選択された列: {selected_column}")

            selected_title=None
            three_way_output_image(st.session_state.Tier_df, selected_column, selected_title, selected_player)
        else:
            st.warning("データフレームが存在しないか空です。")

def player_info():
    st.title("プレイヤー情報")

    st.dataframe(st.session_state.player_df)

    if len(st.session_state.player_df) == 1:
        player_num = 1
    else:
        player_num = st.slider("プレイヤー数", 1, len(st.session_state.player_df), st.session_state.player_num_default)
        st.session_state.player_num_default = player_num

    # プレイヤー名一覧（例：DataFrameから抽出）
    name_options = st.session_state.player_df["名前"].tolist()

    # i 番目のプレイヤー選択に対応したキーを用意
    for i in range(player_num):
        player_key = f"player_select_{i}"

        # セッションステートにキーがなければ初期化
        if player_key not in st.session_state:
            st.session_state[player_key] = name_options[i]  # デフォルト値

        # セレクトボックスを表示（デフォルトを現在のセッションの値に）
        selected_player = st.selectbox(
            label=f"プレイヤー {i+1} を選択してください",
            options=name_options,
            index=name_options.index(st.session_state[player_key]),
            key=player_key  # ここでセッションと自動同期される
        )

        st.write(f"選択されたプレイヤー {i+1}: {selected_player}")

        # image_namesを取得（安全に抽出）
        try:
            image_names_raw = st.session_state.player_df[
                st.session_state.player_df["名前"] == selected_player
            ]["image_names"].values[0]
        except IndexError:
            st.warning("プレイヤーデータが見つかりません。")
            continue

        # image_names をリストに変換（文字列の場合）
        try:
            image_list = ast.literal_eval(image_names_raw) if isinstance(image_names_raw, str) else image_names_raw
            if isinstance(image_list, list) and len(image_list) > 0:
                tier_sum = 0
                for k in range(0, len(image_list), 3):
                    cols = st.columns(3)  # 3つの列を作成
                    for j, image_name in enumerate(image_list[k:k+3]):
                        with cols[j]:
                            # Tierを合計する
                            deck_name = image_name.replace(".png", "")
                            tier_sum += Tier_of_Deck(deck_name)
                            # 画像を出力
                            output_image(st.session_state.df, image_name)
                            if st.button("このデッキを削除",key=f"player_{i}_deck_{j}"):
                                remove_image_name(selected_player, image_name)
                # my_deck_listのtierの平均を計算
                tier_avg = tier_sum / len(image_list)
                truncated_tier_avg = math.floor(tier_avg  * 100) / 100      # 小数点2位以下切り捨て
                st.header(f"Tierの合計：{tier_sum},　　Tierの平均：{truncated_tier_avg}")
            else:
                st.write("デッキが登録されていません")
        except Exception as e:
            st.error(f"画像リストの解析に失敗しました: {e}")
        # 取得したimage_namesの画像をoutput_imageによって画像で出力

        st.write("_____________________________________________________________")

def player_set():
    st.title('PLAYERデータベース')

    # PLAYERを管理するCSVファイルを取得
    # CSV読み込み（セッション内に保持）
    if "player_df" not in st.session_state:
        try:
            st.session_state.player_df = pd.read_csv("player/player.csv")
        except FileNotFoundError:
            st.error("PLAYER.csv が見つかりません。ファイルを正しい場所に置いてください。")
            st.stop()

    st.subheader("プレイヤー一覧")
    
    # データフレームの表示
    st.dataframe(st.session_state.player_df['名前'])

    # PLAYERを追加する機能の追加
    # 入力フォーム
    new_name = st.text_input("追加したい名前を入力してください")

    # 追加ボタン
    if st.button("名前を追加"):
        if new_name.strip() == "":
            st.warning("空白の名前は追加できません。")
        elif new_name in st.session_state.player_df["名前"].values:
            st.warning(f"'{new_name}' はすでにリストに存在します。")
        else:
            # 名前を1行のDataFrameにして追加
            new_row = pd.DataFrame([[new_name]], columns=["名前"])
            player_df = pd.concat([st.session_state.player_df, new_row], ignore_index=True)
            # CSVファイルとして保存
            player_df.to_csv("player/new_player_list.csv", index=False)

            st.success(f"{new_name} を追加しました！")

    # 保存ボタンでセッションとCSVに反映
    if st.button("プレイヤー一覧を保存"):
        try:
            # 一時ファイルがあれば読み込んで session_state に反映
            temp_df = pd.read_csv("player/new_player_list.csv")
            st.session_state.player_df = temp_df
            save_csv()
            st.success("プレイヤー一覧を保存しました！")
        except FileNotFoundError:
            st.error("保存前に名前を追加してください。")

    # 表示
    st.subheader("現在のプレイヤー一覧（未保存の追加も含む）")
    if os.path.exists("player/new_player_list.csv"):
        preview_df = pd.read_csv("player/new_player_list.csv")
        st.dataframe(preview_df['名前'])
    else:
        st.dataframe(st.session_state.player_df['名前'])    

##############################################################################################

def debag():
    st.title("デバッグページ")

 


##############################################################################################


def main():

    init()

    normalize_image_filenames()

    # page_id_list = ["データベース選択","ランダム抽出","Deck_Customize","プレイヤー情報","プレイヤー設定","デバッグページ"]
    page_id_list = ["データベース選択","ランダム抽出","デッキリスト_カスタマイズ","プレイヤー情報","プレイヤー設定"]

    if "page_id" not in st.session_state:
        st.session_state.page_id = "ホーム画面"

    if st.session_state.page_id_flag and st.session_state.page_id is not "ホーム画面":
        page_id = st.sidebar.selectbox("ページ選択", page_id_list)
        st.session_state.page_id = page_id

        # # 保存ボタンでセッションとCSVに反映
        # if st.sidebar.button("プレイヤー一覧を保存",key=f"save_button_1"):
        #     try:
        #         # 一時ファイルがあれば読み込んで session_state に反映
        #         temp_df = pd.read_csv("player/new_player_list.csv")
        #         st.session_state.player_df = temp_df
        #         save_csv()
        #         st.sidebar.success("プレイヤー一覧を保存しました！")
        #     except FileNotFoundError:
        #         st.sidebar.error("保存前に名前を追加してください。")

        # if st.sidebar.button("プレイヤー一覧を初期化(デバック用)"):
        #     try:
        #         # 一時ファイルがあれば読み込んで session_state に反映
        #         temp_df = pd.read_csv("player_list.csv")
        #         st.session_state.player_df = temp_df
        #         shutil.copyfile("player_list.csv", "player/player_list.csv")
        #         shutil.copyfile("player_list.csv", "player/new_player_list.csv")
        #         st.sidebar.success("プレイヤー一覧を初期化しました！")
        #     except FileNotFoundError:
        #         st.sidebar.error("ファイルがありません。")

        chec_box = st.sidebar.checkbox("画面更新用",key="update")
        if chec_box:
            st.sidebar.success("画面が更新されました")

    if st.session_state.page_id == "ホーム画面":
        home_screen()

    if st.session_state.page_id == "データベース選択":
        csv_app()

    if st.session_state.page_id == "データベース作成":
        create_csv()
    
    # 2つのアップロードファイルを結合して作成
    if st.session_state.page_id == "データベース作成_1":
        create_csv_1()

    # 1つのアップロードファイルにデッキを追加して作成
    if st.session_state.page_id == "データベース作成_2":
        create_csv_2()

    # 色からファイルを作成
    if st.session_state.page_id == "データベース作成_3_1":
        create_csv_3_1()

    if st.session_state.page_id == "ランダム抽出":
        random_app()

    if st.session_state.page_id == "デッキリスト_カスタマイズ":
        customize()

    if st.session_state.page_id == "プレイヤー情報":
        player_info()

    if st.session_state.page_id == "プレイヤー設定":
        player_set()

    if st.session_state.page_id == "デバッグページ":
        debag()

if __name__ == "__main__":
    main()
