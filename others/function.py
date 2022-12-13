import requests
import xmltodict
import pandas as pd
from scipy.sparse import csr_matrix
from implicit.als import AlternatingLeastSquares


def get_rating_from_bgg(username):
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
    return result_dict


def get_overall_df(username, result_dict):
    bgg_sep_path = r"others/bggsep.csv"
    data_export = pd.read_csv(bgg_sep_path)
    data_export = data_export.drop(['Unnamed: 0'], axis=1)

    bgg_user_list = [(username, rating, game_id) for game_id, rating in result_dict.items()]
    bgg_user_df = pd.DataFrame(bgg_user_list, columns=['userID', 'rating', 'gameID'])
    data = pd.concat([data_export, bgg_user_df])

    return data


def create_predict(data, username):
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
    rating_sparse.toarray()

    ALS = AlternatingLeastSquares()
    ALS.fit(rating_sparse)

    user_id = [key for key, value in id2user.items() if value == username][0]
    predict_user_ids, predict_user_percents = ALS.recommend(user_id, rating_sparse,
                                                            filter_already_liked_items=False, N=10)

    result = {}
    for num_id, user_id in enumerate(predict_user_ids):
        game_id = id2items[user_id]
        game_name = data[data.gameID == game_id].iloc[0].gameName
        result.update({game_name: round(predict_user_percents[num_id] * 100, 2)})

    return result


def create_str_from_dict(result_dict):
    result_str = ''
    for key, value in result_dict.items():
        result_str += f'{key} - {value}%\n'

    return result_str
