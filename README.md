# Meridian Data Platform

פרויקט Data Engineering לבניית pipeline עבור נתוני הנסיעות הציבוריים של Citi Bike. המערכת קולטת קובצי מקור מ־S3, שומרת אותם ב־Bronze מקומית, מעבדת אותם למודל נסיעות אחיד ב־Silver ומייצרת ב־Gold נתונים יומיים לפי תחנה.

## Business Goal

המטרה העסקית היא לענות על השאלה:

> כמה נסיעות יצאו מתחנה מסוימת וכמה נסיעות הגיעו אליה ביום מסוים?

Departure נספר לפי תחנת המוצא והיום שבו הנסיעה התחילה. Arrival נספר לפי תחנת היעד והיום שבו הנסיעה הסתיימה. נסיעה שמתחילה לפני חצות ומסתיימת לאחר חצות משפיעה על שני ימים שונים.

## Data Source

מקור הנתונים הוא bucket ציבורי של Citi Bike ב־Amazon S3. הוא מכיל קובצי ZIP שבתוכם קובצי CSV של Jersey City ושל New York.

המערכת מגלה את האובייקטים באמצעות S3 XML listing. היא אינה מגרדת את עמוד ה־HTML ואינה בונה URL לפי תבנית קשיחה, משום ששמות הקבצים והסיומות אינם עקביים לאורך השנים.

- Jersey City מזוהה לפי הקידומת `JC-`.
- קובצי New York אינם מכילים בהכרח `nyc` או `new york`, ולכן מזוהים מתוך קובצי הנסיעות שאינם שייכים ל־JC.
- קבצים עשויים להסתיים ב־`.zip` או ב־`.csv.zip`.
- New York פורסמה בקבצים שנתיים עד 2023 ובקבצים חודשיים החל מינואר 2024.
- הסכמה השתנתה לאורך השנים, ובמועד שונה בכל market.
- אותו חלון עשוי להופיע במספר exports, וה־publisher עשוי לפרסם מחדש היסטוריה.

בחירת המקור נעשית מתוך המצאי שה־XML listing מציג בפועל. זיהוי schema נעשה לפי כותרת ה־CSV ולא לפי תאריך קשיח.

## Data Architecture

### Bronze — Source Truth

Bronze שומרת קובצי מקור גולמיים ו־provenance בתוך Docker named volume מקומי. היא אינה ממירה את הנתונים ל־JSON, אינה מבצעת typing או ניקוי ואינה משנה ערכים.

כאשר קיימים מספר exports לאותו חלון, ingestion בוחר export סמכותי אחד לפי המידע שהמקור מספק ושומר אותו בשלמותו. אין לטעון כמה exports ולנסות להסיר כפילויות באמצעות השוואת שורות.

### Silver — Trip Truth

Silver נשמרת ב־PostgreSQL ומכילה שורה אחידה ומטופלת לכל נסיעה תקינה. גרסת הסכמה מזוהה לפי ה־header והשדות ממופים למודל משותף.

נסיעה תקינה חייבת להכיל:

- זמן התחלה;
- זמן סיום;
- מזהה תחנת מוצא;
- מזהה תחנת יעד.

שם תחנה חסר, תחנה שאינה מוכרת מראש או משך נסיעה חשוד אינם סיבות לפסילה בשלב זה.

כאשר `ride_id` קיים במקור הוא נשמר כ־source business key. מאחר שהוא אינו קיים בכל השווקים והסכמות, Silver משתמשת גם ב־surrogate key דטרמיניסטי.

### Quarantine

רשומה שאינה עומדת בתנאי התקינות נשמרת ב־Quarantine ואינה נמחקת. לכל reject נשמרת סיבה עסקית ברורה.

בכל חלון חייב להתקיים:

`published rows = silver rows + rejected rows`

סכום הערכים במפת `reasons` חייב להיות שווה למספר ה־rejects.

### Gold — Business Truth

כל נסיעה תקינה מייצרת שני אירועים לוגיים:

- departure לפי תחנת המוצא ותאריך ההתחלה;
- arrival לפי תחנת היעד ותאריך הסיום.

האירועים מאוגדים ל־`station-daily` בגרעין של market, station ו־day. Gold יכולה לכלול גם DimDate ו־DimStation. ממד התחנות נבנה מתוך תחנות המוצא והיעד ואינו משמש לפסילת נסיעות.

### Report

הדוח קורא את `station-daily` ומחזיר departures ו־arrivals עבור שוק, תחנה ויום.

## Execution Model

המערכת רצה ב־Docker:

- PostgreSQL פועל לאורך חיי הפרויקט.
- Bronze נשמרת בקבצים בתוך Docker named volume מקומי.
- PostgreSQL משתמש ב־volume נפרד.
- PostgreSQL וה־compute containers מחוברים לרשת Docker פנימית משותפת.
- קיים compute image אחד לכל ה־jobs.
- כל `run`, `inspect` או `report` יוצר compute container זמני שמת בסיום.
- state נשמר ב־volumes וב־PostgreSQL, ולא ב־filesystem של compute container.

`just up` מתחיל את חיי הפרויקט ומעלה את התשתית. `just down` מסיים אותם ומסיר את התשתית וה־volumes בהתאם לחוזה הקורס.

## Required Interface

הממשק החיצוני היחיד הוא `just`:

```text
just up
just down

just run     <layer> <job> <window>
just inspect <layer> <job> <window>
just report  daily-station-trips <market> <station> <day>
```

ערכי `run`:

- layer: `ingest-to-bronze`, `transform-to-silver` או `transform-to-gold`;
- job עבור Bronze/Silver: `trips:jc` או `trips:nyc`;
- job עבור Gold: `station-daily`.

ערכי `inspect`:

- layer: `bronze` או `silver`;
- job: `trips:jc` או `trips:nyc`.

Jobs של trips מקבלים חלון חודשי מדויק בפורמט `YYYY-MM`. ה־job של `station-daily` מקבל יום מדויק בפורמט `YYYY-MM-DD`. אין flags, ברירות מחדל או ארגומנטים אופציונליים.

## Output Contract

`inspect` ו־`report` כותבות אובייקט JSON אחד בלבד ל־stdout. לוגים, diagnostics ושגיאות נכתבים ל־stderr.

קלט לא תקין גורם ל־exit code שאינו אפס, להסבר ברור ב־stderr ולאפס כתיבות. המערכת אינה מתקנת אוטומטית window בגרעין שגוי.

## Core Guarantees

- **Job separation:** כל job עצמאי ואינו מפעיל באופן סמוי את קודמו.
- **Network boundary:** רק `ingest-to-bronze` רשאי לגשת לאינטרנט.
- **Idempotency:** הרצה חוזרת אינה מכפילה או משנה את התוצאה.
- **Window independence:** טעינת חלון אחד אינה משנה חלון או market אחר.
- **Atomicity:** כשל אינו משאיר חלון או תשובה חלקיים.
- **Offline rebuild:** ניתן לבנות Silver ו־Gold מחדש מתוך Bronze ללא אינטרנט.
- **Source preservation:** Bronze שומרת raw bytes ו־provenance הנחוץ לזיהוי גרסת המקור.

## Reference Results

| Coordinate | Bronze | Silver | Rejects |
|---|---:|---:|---:|
| `trips:jc 2019-06` | 39,430 | 39,430 | 0 |
| `trips:jc 2026-06` | 109,897 | 109,510 | 387 |
| `trips:nyc 2018-04` | 1,307,543 | 1,307,543 | 0 |

עבור `jc`, תחנה `JC115`, ביום `2026-06-02`, התוצאה היא 216 departures ו־209 arrivals.

## Project Structure

```text
.
├── src/                 Python application
├── sql/
│   ├── init/            PostgreSQL initialization
│   ├── silver/          Silver and quarantine definitions
│   └── gold/            Gold dimensions and facts
├── tests/
│   ├── unit/            Isolated logic tests
│   ├── integration/     Docker, filesystem and PostgreSQL tests
│   └── fixtures/        Small deterministic source samples
├── docs/                Architecture and design decisions
├── Dockerfile           Shared compute image
├── docker-compose.yml   Infrastructure definition
├── justfile             Required external interface
├── requirements.txt     Python dependencies
├── .env.example         Non-secret configuration template
└── README.md
```

Runtime data, Bronze files, PostgreSQL data, secrets and local virtual environments are not committed to Git.
