import io
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Параметры подключения к базе данных Docker
DATABASE_URL = "postgresql://otters:hackathon@localhost:5432/otters_db"
engine = create_engine(DATABASE_URL)

# 2. Ваш текст из файла (вставляем напрямую или читаем из файла)
# Замените этот блок на open("ваш_файл.csv", "r", encoding="utf-8").read(), если запускаете локально
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
Пётр I,800,16000,,,
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

print("1/3 Парсинг новых цен из CSV...")
# Читаем только нужные колонки, убирая пустые "заглушки"
df_new = pd.read_csv(io.StringIO(csv_data.strip())).iloc[:, [0, 1, 2, 5]]
df_new.columns = ["name", "winter", "summer", "stars"]

# Рассчитываем среднюю цену отеля (или можете выбрать df_new['summer'])
df_new["calculated_price"] = ((df_new["winter"] + df_new["summer"]) / 2).round().astype(int)

print("2/3 Загрузка временных данных во временную таблицу базы...")
# Заливаем новые данные как временную таблицу для проведения UPDATE
df_new.to_sql(name="tmp_new_hotel_data", con=engine, if_exists="replace", index=False)

print("3/3 Обновление основной таблицы 'hotels'...")
update_sql = """
UPDATE hotels h
SET 
    -- Если отель найден, обновляем цену
    price = t.calculated_price,
    
    -- Обновляем звезды, ТОЛЬКО если в файле передано валидное значение и оно отличается
    stars = CASE 
        WHEN t.stars IS NOT NULL AND t.stars != h.stars THEN t.stars 
        ELSE h.stars 
    END
FROM tmp_new_hotel_data t
WHERE LOWER(TRIM(h.name)) = LOWER(TRIM(t.name));

-- Удаляем временную таблицу, она больше не нужна
DROP TABLE IF EXISTS tmp_new_hotel_data;

-- СБРАСЫВАЕМ МАТЕРИАЛИЗОВАННОЕ ПРЕДСТАВЛЕНИЕ, ЧТОБЫ ОБНОВИТЬ ВИТРИНУ STREAMLIT
REFRESH MATERIALIZED VIEW mv_hotels_analytics;
"""

with engine.begin() as conn:
    conn.execute(text(update_sql))

print("✅ Цены и звезды успешно обновлены! Материализованный вид mv_hotels_analytics пересобран автоматически.")
