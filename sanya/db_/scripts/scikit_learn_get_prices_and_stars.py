import io
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

# 1. Подключение к базе данных Docker
DATABASE_URL = "postgresql://otters:hackathon@localhost:5432/otters_db"
engine = create_engine(DATABASE_URL)

# Данные вашего CSV-файла
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
Пётр I,8500,16000,,, -- ИСПРАВЛЕНО: убрали ошибочные 800 рублей из хакатон-датасета
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

print("1/4 Загрузка датасета и инфраструктуры...")
df_hotels = pd.read_sql("SELECT id, name, price, stars FROM hotels;", engine)
df_geo = pd.read_sql("""
    SELECT 
        hotel_id, distance_to_metro_meters, distance_to_road_meters, 
        dist_to_main_road_meters, dist_to_mkad_meters, distance_to_shop_meters, 
        distance_to_green_zones_meters, distance_to_where_to_eat_meters, 
        distance_to_attraction_meters, roads_within_100m, crossings_within_100m 
    FROM mv_hotels_analytics;
""", engine)

df_master = pd.merge(df_hotels, df_geo, left_on="id", right_on="hotel_id", how="left")

# Интеграция CSV
df_csv = pd.read_csv(io.StringIO(csv_data.strip())).iloc[:, :4]
df_csv.columns = ["csv_name", "winter", "summer", "csv_stars"]
df_csv["csv_price"] = ((df_csv["winter"] + df_csv["summer"]) / 2).round()

df_master["clean_name"] = df_master["name"].str.strip().str.lower()
df_csv["clean_name"] = df_csv["csv_name"].str.strip().str.lower()
df_master = pd.merge(df_master, df_csv, on="clean_name", how="left")

df_master["price"] = df_master["csv_price"].fillna(df_master["price"])
df_master["stars"] = df_master["csv_stars"].fillna(df_master["stars"])

# --- FEATURE ENGINEERING (УЛУЧШЕНИЕ ПРИЗНАКОВ) ---
geo_cols = [
    "distance_to_metro_meters", "distance_to_road_meters", 
    "dist_to_main_road_meters", "dist_to_mkad_meters", "distance_to_shop_meters", 
    "distance_to_green_zones_meters", "distance_to_where_to_eat_meters", 
    "distance_to_attraction_meters"
]

# Заполняем NaN медианой перед логарифмированием
imputer = SimpleImputer(strategy="median")
df_master[geo_cols] = imputer.fit_transform(df_master[geo_cols])

# Применяем логарифм log1p (чтобы убрать нелинейность расстояний)
for col in geo_cols:
    df_master[f"log_{col}"] = np.log1p(df_master[col])

# Финальный набор признаков для моделей
features = [f"log_{col}" for col in geo_cols] + ["roads_within_100m", "crossings_within_100m"]

print("2/4 Обучение улучшенной модели Ridge Регрессии + Градиентный бустинг для цен...")
# Фильтруем заведомый шум: убираем отели дешевле 1500 руб из обучения, чтобы поднять базовый прогноз
train_p = df_master[(df_master["price"].notna()) & (df_master["price"] >= 1500)]
predict_p = df_master[df_master["price"].isna()]

if len(predict_p) > 0:
    # Используем конвейер: Масштабирование -> Продвинутый Регрессор (Градиентный бустинг над деревьями)
    # Он идеально находит сложные зависимости в ценах
    model_price = make_pipeline(StandardScaler(), GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=4))
    model_price.fit(train_p[features], train_p["price"])
    
    # Предсказываем и ограничиваем минимальную цену (например, 2200 руб), чтобы хостелы не падали в 800 рублей
    pred_res = model_price.predict(predict_p[features]).round().astype(int)
    pred_res = np.clip(pred_res, 2200, None) 
    
    df_master.loc[df_master["price"].isna(), "price"] = pred_res
    print(f"   ► Цены успешно пересчитаны для {len(predict_p)} отелей.")

print("3/4 Обучение классификатора звезд...")
train_s = df_master[df_master["stars"].notna()]
predict_s = df_master[df_master["stars"].isna()]

if len(predict_s) > 0:
    # Для звезд добавляем нормализованную цену как мощный маркер
    stars_features = features + ["price"]
    model_stars = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200, random_state=42, max_depth=6))
    model_stars.fit(train_s[stars_features], train_s["stars"].astype(int))
    
    df_master.loc[df_master["stars"].isna(), "stars"] = model_stars.predict(predict_s[stars_features]).astype(int)
    print(f"   ► Звездность успешно пересчитана.")

print("4/4 Запись реалистичных предсказаний в PostgreSQL...")
with engine.begin() as conn:
    for _, row in df_master.iterrows():
        conn.execute(
            text("UPDATE hotels SET price = :price, stars = :stars WHERE id = :id;"),
            {"price": int(row["price"]), "stars": int(row["stars"]), "id": row["id"]}
        )
    conn.execute(text("REFRESH MATERIALIZED VIEW mv_hotels_analytics;"))

print("🎉 Модель успешно переобучена с использованием нормализации, логарифмирования и защиты от аномалий!")
