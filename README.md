# regadd — Python port of the CARS registration screen

Port of the `drop` / `add` / `swap` screen from C + Informix ESQL/C to Python 3.10+.  
Standard library only (`sqlite3`). `pytest` is the only dev dependency.

---

## Структура файлів

```
regadd/
├── db.py                  # DAO layer (порт db.ec) — один SQL-запит на функцію
├── proc.py                # Бізнес-логіка (порт proc.ec) — do_drop / do_add / do_swap
├── main.py                # Тонкий вхід (порт main.c) — argv, print, exit
├── data/
│   ├── schema.sqlite.sql
│   └── seed.sqlite.sql
└── tests/
    └── test_scenarios.py  # S1–S15 + додаткові edge-кейси (22 тести)
```

---

## Запуск

### Підготовка БД

```bash
python3 - <<'EOF'
import sqlite3
def load(p):
    with open(p) as f: return f.read()
conn = sqlite3.connect("cars.db", isolation_level=None)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(load("data/schema.sqlite.sql"))
conn.executescript(load("data/seed.sqlite.sql"))
conn.close()
EOF
```

За замовчуванням `main.py` шукає `cars.db` поруч із собою.  
Можна перевизначити через змінну оточення:

```bash
export CARSDB=/path/to/cars.db
```

### CLI-контракт

```bash
python3 main.py drop <id> <sec> <yr> <sess>
python3 main.py add  <id> <sec> <yr> <sess>
python3 main.py swap <id> <dropsec> <addsec> <yr> <sess>
```

### Запуск сценаріїв S1–S15 вручну

Кожен сценарій потребує свіжої БД. Скрипт нижче перестворює її перед кожним запуском:

```bash
for args in \
  "drop 1001 CS101-01 2024 S" \
  "drop 1002 CS101-02 2024 S" \
  "drop 1003 CS101-01 2024 S" \
  "drop 1004 CS101-01 2024 S" \
  "drop 1001 HX999-01 2023 F" \
  "drop 1007 CS101-02 2024 S" \
  "add 1007 CS101-02 2024 S" \
  "add 1007 CS201-01 2024 S" \
  "add 1007 PHIL300-1 2024 S" \
  "add 1008 PHIL300-1 2024 S" \
  "add 1001 MA200-01 2024 S" \
  "add 1007 HX999-01 2023 F" \
  "add 1007 CS101-01 2024 S" \
  "swap 1001 CS101-01 CS201-01 2024 S" \
  "swap 1001 MA200-01 CS999-01 2024 S"
do
  # rebuild DB
  python3 -c "
import sqlite3
c=sqlite3.connect('cars.db',isolation_level=None)
c.execute('PRAGMA foreign_keys=ON')
c.executescript(open('data/schema.sqlite.sql').read())
c.executescript(open('data/seed.sqlite.sql').read())
c.close()
"
  python3 main.py $args
  echo "  exit=$?"
done
```

### Автотести (pytest)

```bash
pip install pytest
python3 -m pytest tests/ -v
```

Всі тести використовують in-memory БД — ніяких файлів на диску не потрібно.

---

## Архітектурні рішення

### Три шари

| Файл | Оригінал | Відповідальність |
|------|----------|-----------------|
| `db.py` | `db.ec` | Один SQL-запит на функцію, нуль бізнес-логіки. Повертає ті самі коди що й оригінал (`REG_OK`/`REG_FAIL`/`RG_NOTENR`/`TRUE`/`FALSE`/лічильник). |
| `proc.py` | `proc.ec` | `do_drop` / `do_add` / `do_swap`. Зберігає точний порядок перевірок з оригіналу. |
| `main.py` | `main.c` | Парсинг argv, виклик proc, `rg_message()`, `print`, `sys.exit`. |

### Транзакційність

Оригінал відкриває транзакцію в `db_open()` (`$BEGIN WORK`) і комітить / робить роллбек в `db_close()` залежно від `trial_run`. У Python це складніше, бо `sqlite3` з `isolation_level=None` (autocommit) вимагає явного `BEGIN`.

Прийняте рішення:
- `db_open()` виконує `BEGIN` — аналог `$BEGIN WORK`.
- `do_drop` і `do_add` самі виконують `COMMIT` при успіху і одразу `BEGIN` (щоб з'єднання залишалось у транзакційному стані для housekeeping в `main.py`).
- При `REG_FAIL` proc просто повертає код без коміту. `main.py` викликає `db_close(conn, commit=False)` → `ROLLBACK`.
- Окрема рання точка виходу `do_add` (waitlist branch) комітить і повертає `RG_WAITED` — точно як `$COMMIT WORK; return(RG_WAITED)` в оригіналі.

### Атомарний swap (A+)

`do_swap` НЕ делегує в `do_drop`/`do_add` напряму (вони комітять всередині). Замість цього:

1. `SAVEPOINT swap_point` — вкладений savepoint поверх активної транзакції.
2. `_do_drop_no_commit` — вся логіка drop без COMMIT.
3. Якщо drop провалився → `ROLLBACK TO swap_point` + `RELEASE` → повертаємо помилку drop.
4. `_do_add_no_commit` — вся логіка add без COMMIT.
5. Якщо add провалився → `ROLLBACK TO swap_point` (відкочує і drop!) + `RELEASE` → повертаємо помилку add.
6. Якщо обидва успішні → `RELEASE swap_point` → `COMMIT` → `BEGIN`.

Таким чином S15 (`swap MA200-01 CS999-01`) повертає `RG_NOTENR` (секція не існує) і MA200-01 залишається зарахованою — повний роллбек обох частин.

---

## Edge-кейси поза S1–S15

### Неіснуюча секція при `add`
`sect_crs()` повертає `RG_NOTENR` (той самий код що й "not found" в оригіналі — `SQLNOTFOUND` на `sec_rec`). Повідомлення: `"Student is not enrolled in that section."`, exit 1. Покрито тестом `test_add_nonexistent_section`.

### Неіснуючий студент
`has_hold()` поверне `FALSE` (0 active holds). `find_enr()` поверне `RG_NOTENR`. Операція завершиться з `"Student is not enrolled in that section."`. Поведінка збігається з оригіналом (немає окремої перевірки існування студента в `stu_rec`).

### Inactive hold
`has_hold` рахує лише рядки з `active='Y'`. Alice має hold з `active='N'` — ігнорується. Покрито тестом `test_inactive_hold_ignored`.

### Withdrawn grade (`'W '`) при drop
Оригінал дозволяє дропати записи з `grade='W '` (withdrawn). Покрито тестом `test_drop_withdrawn_grade_allowed`.

### `count_enr` vs поріг `set_inactive`
Рахується ДО видалення. Якщо `active == 1` → це остання активна реєстрація → після видалення студент стає `enrolled='N'`. Покрито тестом `test_S2_drop_only_course_sets_inactive`.

### `term_credits` коли немає жодного запису
`COALESCE(sum(...), 0)` → повертає 0, не `REG_FAIL`. Оригінал перевіряє `SQLCODE == SQLNOTFOUND; return(0)`.

### Waitlist position overflow
`next_wait_pos` повертає `max(position)+1`. Якщо waitlist порожній — `max()` повертає `NULL`, ми повертаємо 1. Покрито тестом `test_waitlist_position_increments`.
