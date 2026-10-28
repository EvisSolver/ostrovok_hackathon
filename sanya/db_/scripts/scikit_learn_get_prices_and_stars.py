# -*- coding: utf-8 -*-
"""Пересчёт цен (руб./ночь) и звёзд отелей: PostgreSQL + CSV-датасет.
Цена: лог-линейная Ridge vs GradientBoosting vs их бленд - выбор по кросс-валидации.
Звёзды: порядковая Ridge-регрессия по тем же признакам + log(цены)."""
import io, re, difflib, warnings
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import GradientBoostingRegressor, VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import make_scorer
from sklearn.model_selection import RepeatedKFold, KFold, cross_validate, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import QuantileTransformer

warnings.filterwarnings("ignore")

DATABASE_URL = "postgresql://otters:hackathon@localhost:5432/otters_db"
MIN_TRAIN_PRICE = 1500   # дешевле - шум, в обучение не берём
MIN_PRED_PRICE = 2200    # границы прогноза, руб./ночь
MAX_PRED_PRICE = 26000
SEED = 42

# Пётр I: убраны ошибочные 800 руб. из хакатон-датасета. Комментарии внутри CSV недопустимы.
csv_data = """name,winter,summer,,,stars
Славянка,3200,3500,,,
Два Льва,2250,4750,,,
Максима Заря,2400,3500,,,
Валс,2250,2600,,,
Дельта,3900,5500,,,
Арктика,3100,2950,,,
Аквамарин,6000,9000,,,
Медея,5200,5400,,,
Мехмонхона,2500,4000,,,
Садовое Кольцо,8000,13000,,,
Града,7000,8300,,,
На Красной Пресне,6400,3800,,,
Шерстон,3190,3900,,,
Lottle Hottle Moscow,46000,55000,,,
Будашепт,6930,7600,,,
InterContinental Moscow Tverskaya,7000,13000,,,5
Azimut Moscow Tulskaya Hotel,3300,4250,,,
Инсайд Бизнес,3500,4350,,,
Maxima Panorama,4700,6850,,,
Кадашевская,7800,9000,,,
Пётр I,8500,16000,,,
Mercure Arbat Moscow,7200,9000,,,
Mercure Москва Бауманская,5300,8900,,,
Adagio Москва Павелецкая,5600,7650,,,
Спектрсити,5400,7000,,,
Минт,2500,3250,,,
Звезды Арбата,7000,10500,,,
Hampton by Hilton Moscow Strogino,8100,9450,,,
Moscow Holiday,4000,4700,,,
Аэрополис,3000,5000,,,
Сухаревский,6500,8000,,,
Красные Ворота,2400,4000,,,
Графский,9450,11000,,,
Уютный дом,1900,3200,,,
Имрус,4200,7000,,,
Авита Красные Ворота,4100,4750,,,
Florinn,3200,4500,,,
Мост,4500,6000,,,
Столичная,4900,5500,,,
Эрмитаж,4200,5500,,,
Богемия,4000,5000,,,
Арум-Отель,6300,8900,,,
Комфорт класс,2400,3500,,,
Гипноз,4700,6600,,,
Пафос,3100,4400,,,
People Loft Tverskaya,3700,4300,,,3
Тема,7000,5500,,,
Коломенское,4200,4700,,,
Неаполь,3800,5800,,,
Marrko Hotel,3100,4100,,,
Наумов,5000,5700,,,
Брусника Холдинг,1400,2100,,,
Barin Residence Balchug,5500,8800,,,
Хованский,4900,6000,,,
Адам,2000,3300,,,
Чехов,9600,11500,,,5
Арт Москва Войковская,3600,4250,,,
Barin Residence Myasnitskaya,7800,10000,,,4
Barin Residence Grand,8700,11000,,,
Gravor,3700,4200,,,
Fili House,4250,5000,,,
Библиотека,1700,3000,,,
Силуэт,2700,3500,,,
Петровский путевой дворец,8000,12000,,,
Library Hotel,4600,3900,,,
WineWood Moscow,6100,11500,,,
Подъезд №2,2700,3400,,,
Артхофф,3950,5100,,,
Южный порт,3900,4700,,,
Diamond Apartments,16000,21000,,,
Концерт на Таганской,2500,3850,,,
Greenstone,4500,6500,,,
Квадро,2000,3600,,,
Олимп,3900,4050,,,
Botanic Garden,4500,5500,,,
Максима Ирбис отель,3300,4000,,,
Сафмар Палас Отель,5600,12000,,,5
Вега,4200,5000,,,
Гамма,3550,4000,,,
Mamaison All-Suites Spa Hotel Pokrovka,10000,12000,,,
Президент-Отель,9600,12000,,,
Арбат,7200,9000,,,
Марко Поло Пресня,7000,10000,,,
Ibis Dynamo Moscow,3400,4000,,,
Пушкин,6700,8000,,,
Select Paveletskaya,4600,5500,,,
Альфа,4000,5000,,,
Бета,2400,3700,,,
Академическая,3500,4300,,,
Даниловская,6900,7700,,,
Gentalion,5500,7500,,,
Арткорт Москва Центр,7500,11500,,,
Hilton Moscow Leningradskaya,7200,800,,,
Концерт,2150,4100,,,2
На Казачьем,5100,6000,,,
Воронцовский,4000,5500,,,
DoubleTree by Hilton Hotel Moscow - Marina,10200,13000,,,
DoubleTree by Hilton Moscow - Vnukovo Airport,13500,16000,,,
Stand Art,18000,23000,,,"""

GEO = ["distance_to_metro_meters", "distance_to_road_meters", "dist_to_main_road_meters",
       "dist_to_mkad_meters", "distance_to_shop_meters", "distance_to_green_zones_meters",
       "distance_to_where_to_eat_meters", "distance_to_attraction_meters"]
COUNTS = ["roads_within_100m", "crossings_within_100m"]
KEYWORDS = {  # ключевые слова в названии - маркер ценового сегмента
    "kw_luxury": "hilton|intercontinental|doubletree|marriott|radisson|hyatt|kempinski|lotte|lottle|"
                 "sheraton|palace|палас|grand|гранд|дворец|president|президент|mamaison",
    "kw_mid": "mercure|novotel|holiday|hampton|adagio|azimut|азимут|maxima|максима|select|бизнес|"
              "residence|резиденс|spa|спа",
    "kw_budget": "ibis|ибис|хостел|hostel|мини|mini|комфорт|эконом|общежит|капсул|уютный|комнат|"
                 "гостевой|подъезд",
    "kw_apart": "apart|апарт|suites|loft|лофт|квартир|house",
}
FEATURES = GEO + COUNTS + list(KEYWORDS) + ["name_latin"]


def norm(s):
    return re.sub(r"\s+", " ", str(s).lower().replace("ё", "е").replace('"', "")).strip()


def ridge():
    # QuantileTransformer: убирает перекосы расстояний и ОБРЕЗАЕТ значения вне диапазона обучения,
    # поэтому линейная модель не может экстраполировать нетипичный отель в 50 000 руб.
    return make_pipeline(SimpleImputer(strategy="median"),
                         QuantileTransformer(output_distribution="normal", n_quantiles=50),
                         RidgeCV(alphas=np.logspace(-2, 3, 40)))


def gbr():
    return make_pipeline(SimpleImputer(strategy="median"), GradientBoostingRegressor(
        loss="huber", n_estimators=300, learning_rate=0.05, max_depth=3,
        subsample=0.8, min_samples_leaf=5, random_state=SEED))


def log_target(reg):  # учим log(цены) -> модель минимизирует ошибку в процентах, а не в рублях
    return TransformedTargetRegressor(regressor=reg, func=np.log1p, inverse_func=np.expm1)


def rmsle(y, p):
    return float(np.sqrt(np.mean((np.log1p(y) - np.log1p(np.clip(p, 1, None))) ** 2)))


def select_price_model(X, y):
    cands = {"Ridge (лог-линейная)": log_target(ridge()),
             "GradientBoosting": log_target(gbr()),
             "Blend Ridge+GBR": log_target(VotingRegressor([("r", ridge()), ("g", gbr())]))}
    if len(y) < 20:
        return "Ridge (лог-линейная)", cands["Ridge (лог-линейная)"]
    scoring = {"rmsle": make_scorer(rmsle, greater_is_better=False),
               "mape": "neg_mean_absolute_percentage_error"}
    cv = RepeatedKFold(n_splits=5, n_repeats=2, random_state=SEED)
    best, best_score = None, np.inf
    print(f"   Кросс-валидация (5-fold x 2), n={len(y)}:")
    for name, m in cands.items():
        r = cross_validate(m, X, y, cv=cv, scoring=scoring, n_jobs=-1)
        s = -r["test_rmsle"].mean()
        print(f"      {name:<22} RMSLE={s:.3f}  MAPE={-r['test_mape'].mean():.1%}")
        if s < best_score:
            best, best_score = name, s
    return best, cands[best]


def main():
    engine = create_engine(DATABASE_URL)
    # Флаги "значение предсказано моделью": при повторном запуске не учимся на своих же прогнозах
    have = {c["name"] for c in inspect(engine).get_columns("hotels")}
    with engine.begin() as conn:
        for col in ("price_is_predicted", "stars_is_predicted"):
            if col not in have:
                conn.execute(text(f"ALTER TABLE hotels ADD COLUMN {col} BOOLEAN NOT NULL DEFAULT FALSE"))

    print("1/4 Загрузка данных...")
    df = pd.read_sql("SELECT id, name, price, stars, price_is_predicted, stars_is_predicted FROM hotels", engine)
    geo = pd.read_sql(f"SELECT hotel_id, {', '.join(GEO + COUNTS)} FROM mv_hotels_analytics", engine)
    df = df.merge(geo, left_on="id", right_on="hotel_id", how="left")
    df.loc[df["price_is_predicted"].astype(bool), "price"] = np.nan
    df.loc[df["stars_is_predicted"].astype(bool), "stars"] = np.nan
    df["price"] = pd.to_numeric(df["price"], errors="coerce").where(lambda s: s > 0)
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce").where(lambda s: s > 0)
    df["clean_name"] = df["name"].map(norm)

    # CSV: средняя по сезонам; если сезоны отличаются >3 раз (опечатка вида 7200/800) - берём большую
    csv = pd.read_csv(io.StringIO(csv_data))[["name", "winter", "summer", "stars"]]
    lo, hi = csv[["winter", "summer"]].min(axis=1), csv[["winter", "summer"]].max(axis=1)
    csv["csv_price"] = np.where(lo / hi < 0.35, hi, (lo + hi) / 2).round()
    csv["csv_stars"] = pd.to_numeric(csv["stars"], errors="coerce")
    csv["clean_name"] = csv["name"].map(norm)
    db_names = df["clean_name"].unique().tolist()
    for i, nm in csv["clean_name"].items():  # нечёткое сопоставление опечаток ("Lottle Hottle" -> "Lotte Hotel")
        if nm not in db_names:
            close = difflib.get_close_matches(nm, db_names, n=1, cutoff=0.85)
            print(f"   ~ '{nm}' -> '{close[0]}'" if close else f"   ! нет в БД: {nm}")
            if close:
                csv.at[i, "clean_name"] = close[0]
    csv = csv[["clean_name", "csv_price", "csv_stars"]].drop_duplicates("clean_name")
    df = df.merge(csv, on="clean_name", how="left")
    df["price"] = df["csv_price"].fillna(df["price"])
    df["stars"] = df["csv_stars"].fillna(df["stars"])
    df.loc[df["csv_price"].notna(), "price_is_predicted"] = False
    df.loc[df["csv_stars"].notna(), "stars_is_predicted"] = False

    for col, pat in KEYWORDS.items():
        df[col] = df["clean_name"].str.contains(pat).astype(int)
    df["name_latin"] = df["clean_name"].str.contains("[a-z]").astype(int)
    print(f"   отелей {len(df)}, с ценой {df['price'].notna().sum()}, со звёздами {df['stars'].notna().sum()}")

    print("2/4 Цена...")
    train = df[df["price"] >= MIN_TRAIN_PRICE]
    y = train["price"].clip(upper=MAX_PRED_PRICE)  # единичные выбросы (50 000) не тянут модель вверх
    name, model = select_price_model(train[FEATURES], y)
    model.fit(train[FEATURES], y)
    mask = df["price"].isna()
    if mask.any():
        pred = np.clip(model.predict(df.loc[mask, FEATURES]), MIN_PRED_PRICE, MAX_PRED_PRICE).round()
        df.loc[mask, "price"], df.loc[mask, "price_is_predicted"] = pred, True
        print(f"   ► {name}: предсказано {mask.sum()} цен; медиана {np.median(pred):,.0f}, "
              f"max {pred.max():,.0f}, упёрлись в потолок {MAX_PRED_PRICE}: {(pred >= MAX_PRED_PRICE).sum()}")
    else:
        print("   ! Нет отелей без цены - модели нечего предсказывать.")

    print("3/4 Звёзды...")
    df["log_price"] = np.log1p(df["price"])
    feats = FEATURES + ["log_price"]
    tr, mask = df[df["stars"].notna()], df["stars"].isna()
    if mask.any():
        if len(tr) >= 10:  # порядковая регрессия: предсказываем число звёзд и округляем
            cv_pred = cross_val_predict(ridge(), tr[feats], tr["stars"], cv=KFold(5, shuffle=True, random_state=SEED))
            print(f"   CV MAE звёзд: {np.abs(np.clip(np.rint(cv_pred), 1, 5) - tr['stars']).mean():.2f} (n={len(tr)})")
            pred = np.clip(np.rint(ridge().fit(tr[feats], tr["stars"]).predict(df.loc[mask, feats])), 1, 5)
        else:  # разметки мало - по рангу цены
            q = df.loc[mask, "price"].rank(pct=True).to_numpy()
            pred = np.select([q <= .15, q <= .5, q <= .85], [2, 3, 4], 5)
        df.loc[mask, "stars"], df.loc[mask, "stars_is_predicted"] = pred, True
        print(f"   ► предсказано {mask.sum()} звёзд: {pd.Series(pred).astype(int).value_counts().sort_index().to_dict()}")

    print("4/4 Запись в PostgreSQL...")
    rows = [dict(id=int(r.id), price=int(r.price), stars=int(r.stars),
                 pp=bool(r.price_is_predicted), sp=bool(r.stars_is_predicted)) for r in df.itertuples()]
    with engine.begin() as conn:
        conn.execute(text("UPDATE hotels SET price=:price, stars=:stars, price_is_predicted=:pp, "
                          "stars_is_predicted=:sp WHERE id=:id"), rows)
        if engine.dialect.name == "postgresql":
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_hotels_analytics"))
    print(f"🎉 Обновлено {len(rows)} отелей. Модель цены: {name}")


if __name__ == "__main__":
    main()
