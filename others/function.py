import requests
import xmltodict
import pandas as pd
from scipy.sparse import csr_matrix
from implicit.als import AlternatingLeastSquares
from io import StringIO
from time import sleep
import numpy as np
from enum import Enum, auto


class Method(Enum):
    recommend = auto()
    similar = auto()


def get_rating_from_bgg_xml(username):
    url = f'https://boardgamegeek.com/xmlapi2/collection?username={username}'
    items = None
    for i in range(10):
        response = requests.get(url)
        data = xmltodict.parse(response.content)
        if 'items' in data.keys():
            items = data['items']['item']
            break

    if not items:
        return None

    result_dict = {}
    for item in items:
        game_id = item['@objectid']
        if 'stats' in item.keys():
            stats = item['stats']
            if 'rating' in stats.keys():
                rating = stats['rating']
                if '@value' in rating.keys():
                    value = rating['@value']
                    try:
                        value_float = float(value)
                        result_dict[game_id] = value_float
                    except Exception as ex:
                        pass

    bgg_user_list = [(username, rating, game_id) for game_id, rating in result_dict.items()]
    result_df = pd.DataFrame(bgg_user_list, columns=['userID', 'rating', 'gameID'])

    return result_df


def get_rating_from_bgg_csv(username):
    for _ in range(5):
        try:
            url = f"https://boardgamegeek.com/geekcollection.php?action=exportcsv" \
                  f"&subtype=boardgame&username={username}&all=1exporttype=csv"
            r = requests.get(url)
            content = r.content.decode()
            csvStringIO = StringIO(content)
            df = pd.read_csv(csvStringIO, sep=",", header=0)
            user_df = df[['objectid', 'rating']]
            user_df = user_df.rename(columns={'objectid': 'gameID'})
            user_df.insert(0, "userID", username)
            return user_df
        except Exception:
            sleep(1)
    return None


def load_data_from_file():
    bgg_sep_path = r"others/bggsep.csv"
    data_export = pd.read_csv(bgg_sep_path)
    data_export = data_export.drop(['Unnamed: 0'], axis=1)
    return data_export


def get_overall_df(user_df):
    data_export = load_data_from_file()
    data = pd.concat([data_export, user_df])
    return data


def get_game_id_by_name(data, game_name):
    unique_items = data['gameID'].unique()
    id2items = {key: value for key, value in enumerate(unique_items)}
    game_ids = data.loc[data.gameName == game_name]

    if not game_ids.empty:
        game_id = game_ids.iloc[0].gameID
        inv_id2items = {value: key for key, value in id2items.items()}
        game_order_id = inv_id2items.get(game_id)
        return int(game_order_id)

    return None


def predict(data, value, number, method):
    unique_users = data['userID'].unique()
    unique_items = data['gameID'].unique()
    id2user = {key: value for key, value in enumerate(unique_users)}
    id2items = {key: value for key, value in enumerate(unique_items)}
    rating = list(data.rating)

    user2id = {value: key for key, value in id2user.items()}
    items2id = {value: key for key, value in id2items.items()}

    rows = data.userID.map(user2id)
    cols = data.gameID.map(items2id)

    rating_sparse = csr_matrix((rating, (rows, cols)), shape=(len(user2id), len(items2id)))

    ALS = AlternatingLeastSquares()
    ALS.fit(rating_sparse)

    if method == Method.similar:
        user_pred, user_pred_percents = predict_similar_games(ALS, data, value, number)
    else:
        user_pred, user_pred_percents = create_predict(ALS, id2items, number, rating_sparse, user2id, value)

    result = {}
    for num, game_id in enumerate(user_pred):
        game_name = data[data.gameID == game_id].iloc[0].gameName
        percent = round(user_pred_percents[num] * 100, 2)
        result.update({game_name: percent})

    return result


def predict_similar_games(ALS, data, game_id, number):
    predict_games, predict_percents = ALS.similar_items(game_id, number + 1)
    unique_items = data['gameID'].unique()
    id2items = {key: value for key, value in enumerate(unique_items)}
    user_pred = [id2items[i] for i in predict_games][1:]
    user_pred_percents = predict_percents[1:]
    return user_pred, user_pred_percents


def create_predict(ALS, id2items, number, rating_sparse, user2id, username):
    user_ids = np.arange(rating_sparse.shape[0])
    predict_games, predict_percents = ALS.recommend(user_ids, rating_sparse,
                                                    filter_already_liked_items=True, N=number)
    user_pred = [id2items[i] for i in predict_games[user2id[username], :]]
    user_pred_percents = predict_percents[user2id[username], :]
    return user_pred, user_pred_percents


def create_str_from_dict(result_dict):
    result_str = ''
    for key, value in result_dict.items():
        result_str += f'{key} - {value}%\n'

    return result_str
