# System Architecture

## Purpose

המערכת קולטת נתוני נסיעות של Citi Bike מ־S3 ומייצרת תשובה יומית לפי שוק ותחנה. הארכיטקטורה מפרידה בין compute זמני ל־storage מתמשך, בין מקור גולמי למשמעות עסקית ובין jobs שניתן להריץ באופן עצמאי.

## High-Level Data Flow

```text
Public S3 XML listing and archives
                 │
                 │ Internet allowed
                 ▼
     Temporary ingestion container
                 │
                 ▼
     Local Bronze Docker volume
       raw files + provenance
                 │
                 │ No internet from here
                 ▼
      Temporary Silver container
                 │
        ┌────────┴────────┐
        ▼                 ▼
 Silver trips       Quarantine
        │            PostgreSQL
        └────────┬────────┘
                 ▼
       Temporary Gold container
                 │
                 ▼
 Gold station events and station-daily
              PostgreSQL
                 │
                 ▼
       Temporary report container
                 │
                 ▼
            One JSON object
```

## Main Architectural Decisions

### Local File-Based Bronze

Bronze נשמרת בקבצים בתוך Docker named volume מקומי ולא בטבלת PostgreSQL. כך נשמר תוכן המקור ללא כפיית schema, הקבצים משותפים בין containers זמניים וניתן לבנות מחדש את השכבות הבאות ללא אינטרנט.

ה־volume נמצא פיזית בדיסק המקומי אך מנוהל על ידי Docker. הוא קיים לאורך חיי הפרויקט ונמחק על ידי `just down` בהתאם לחוזה הקורס.

### PostgreSQL from Silver Onward

Silver, Quarantine ו־Gold נשמרים ב־PostgreSQL. מסד הנתונים מספק typing, constraints, transactions, החלפה אטומית של windows ואגרגציות עקביות.

### Ephemeral Compute

אין Python service קבוע. כל job נוצר כ־container זמני מאותו compute image, מבצע אחריות אחת ומסתיים. הנתונים נשמרים ב־Bronze volume או ב־PostgreSQL ולא בתוך ה־container.

### One Job per Responsibility

Ingestion, Silver ו־Gold הם jobs עצמאיים. כל אחד ניתן להרצה ולבדיקה בלי להפעיל באופן סמוי את jobs האחרים.

### Source-Driven Discovery

שמות קבצים אינם נבנים מתבנית. Ingestion קורא את S3 XML listing ובוחר מתוך מה שהמקור מפרסם בפועל.

### Header-Driven Conformance

Silver מזהה את גרסת הסכמה לפי כותרת ה־CSV ולא לפי תאריך migration קשיח.

## Runtime Components

### PostgreSQL Service

PostgreSQL הוא container מתמשך בעל שם service עקבי ברשת Docker. הוא עולה ב־`just up` ונשאר זמין לכל compute container עד `just down`.

תחומי האחריות שלו:

- אחסון Silver ו־Quarantine;
- אחסון Gold;
- שמירת constraints ומפתחות;
- החלפת window בתוך transaction;
- מתן תשובה ל־inspect ול־report.

### Bronze Volume

Docker named volume מקומי המשותף לכל compute containers. הוא מכיל raw source files ו־manifest לכל coordinate.

### PostgreSQL Volume

Volume נפרד לקובצי PostgreSQL. ההפרדה מונעת ערבוב בין raw source artifacts לבין storage פנימי של מסד הנתונים.

### Shared Network

רשת Docker פנימית מחברת את PostgreSQL ואת ה־compute containers. ה־compute containers ניגשים למסד לפי שם ה־service ולא לפי כתובת IP משתנה.

### Compute Image

Image יחיד כולל את אפליקציית Python, ה־dependencies וקובצי SQL הנדרשים. אותו image משמש לכל jobs כדי למנוע הבדלים בין סביבות ההרצה.

### Temporary Compute Containers

כל `run`, `inspect` או `report` יוצר container חדש. ה־container מתחבר לרשת ול־volumes הנדרשים, מבצע פעולה אחת, מחזיר exit code ומוסר בסיום.

## Component Lifetime

רכיבים מתמשכים בזמן חיי הפרויקט:

- PostgreSQL container;
- Bronze volume;
- PostgreSQL volume;
- shared Docker network.

רכיבים זמניים:

- ingestion containers;
- Silver transformation containers;
- Gold transformation containers;
- inspect containers;
- report containers.

## Lifecycle

### `just up`

`just up` אינו מקבל inputs ואינו מעבד נתונים. הוא יוצר את הרשת ואת שני ה־volumes, מעלה את PostgreSQL, ממתין עד שהוא מוכן ומאתחל schemas ואובייקטים בסיסיים באופן idempotent.

### `just run`

`just run` מקבל layer, job ו־window. הוא מאמת את הקלט, יוצר compute container זמני, מחבר אותו לתשתית, מפעיל job אחד, מעביר את ה־exit code ומסיר את ה־container בסיום.

### `just inspect`

`inspect` קורא state קיים ואינו מפעיל transformation. Bronze inspection קורא את ה־manifest המקומי ו־Silver inspection קורא את PostgreSQL. הפלט הוא אובייקט JSON יחיד.

### `just report`

`report` קורא את Gold ואינו בונה אותה מחדש. הוא מחזיר אובייקט JSON יחיד עבור השאלה העסקית.

### `just down`

`just down` מסיים את חיי הפרויקט, עוצר ומסיר containers, מסיר את הרשת ומוחק את Bronze ואת PostgreSQL volumes. לאחר `just down` ואז `just up`, המערכת מתחילה מ־state ריק.

## Network Boundary

גישה לאינטרנט מותרת רק ל־`ingest-to-bronze`, שקורא את ה־XML listing ומוריד את המקור שנבחר. Silver, Gold, inspect ו־report משתמשים רק ב־Bronze volume וב־PostgreSQL. גם כאשר נתיב האינטרנט חסום, ניתן לבנות מחדש את Silver ואת Gold מתוך Bronze.

## Bronze Design

### Logical Partitioning

Bronze מחולקת רעיונית לפי source, market, year ו־month:

```text
bronze/
└── trips/
    ├── jc/
    │   └── 2026/06/
    │       ├── versions/
    │       └── manifest
    └── nyc/
        └── 2018/04/
            ├── versions/
            └── manifest
```

המבנה הפיזי המדויק ייקבע בזמן המימוש, אך coordinate של חלון נסיעות נשאר market וחודש.

### Raw Data and Provenance

Bronze שומרת את הבתים של קובצי ה־CSV שנבחרו ללא שינוי. אין בה typing, normalization, schema conformance, business validation או row-level de-duplication.

אפשר לשמור archive שהורד כמטמון, אך ה־manifest של החלון מגדיר במפורש אילו members מרכיבים את ה־export הפעיל. לכל coordinate נשמרים לפחות:

- source, market ו־window;
- S3 object key, last modified וגודל;
- checksum או fingerprint;
- selected archive members וה־timestamps שלהם;
- published row count;
- ingestion timestamp;
- source version identity והגרסה הפעילה.

ה־manifest נכתב אחרון ובאופן אטומי, כדי שחלון לא ייראה מוכן אם הכתיבה נקטעה.

### Export Selection

בחירת export מתבצעת ב־ingestion:

1. לזהות אובייקטים המכסים את market וה־window;
2. לפתוח את ה־archive;
3. לזהות members השייכים לחלון;
4. לקבץ members לפי export run;
5. לבחור את ה־run האחרון לפי timestamps ומבנה התיקיות;
6. לקחת את ה־run בשלמותו.

אין לטעון כמה exports ולבצע `DISTINCT`. הבדלים זעירים בייצוג floating-point הופכים השוואת שורות לשיטה לא אמינה.

אם fingerprint זהה לגרסה שכבר נקלטה, ingestion אינו יוצר state נוסף. אם המקור השתנה, נשמרת גרסה חדשה וההפניה לגרסה הפעילה מתעדכנת בלי למחוק בשקט את הקודמת בזמן חיי הפרויקט.

## Silver Design

Silver קוראת רק את ה־manifest הפעיל ואת קובצי Bronze המקומיים. היא מזהה schema לפי header, ממפה שדות, ממירה טיפוסים ומפעילה את כלל התקינות.

נסיעה תקינה כוללת start timestamp, end timestamp, start station ID ו־end station ID. כל רשומה אחרת נשמרת ב־Quarantine עם סיבה עסקית.

`source_ride_id` נשמר כאשר הוא קיים. בנוסף נוצר surrogate key דטרמיניסטי על בסיס provenance ומיקום הרשומה במקור הפעיל. המפתח הטכני אינו משמש להשוואת נסיעות בין exports.

גרעין טעינת Silver הוא market וחודש. החלפת חלון מתבצעת בתוך transaction ומשפיעה רק על אותו coordinate. לפני commit נבדק:

`published rows = valid silver rows + quarantine rows`

כשל גורם ל־rollback ומשאיר את הגרסה התקינה הקודמת ללא שינוי.

## Gold Design

כל נסיעה תקינה מייצרת שני אירועים:

| Event | Station | Day |
|---|---|---|
| Departure | start station | date of start timestamp |
| Arrival | end station | date of end timestamp |

DimDate מספק מאפייני תאריך. DimStation נבנה מאיחוד תחנות המוצא והיעד ואינו משמש לאימות נסיעות.

גרעין `station-daily` הוא `market + station + day`, והמדדים הם departures ו־arrivals. תחנה בעלת אירועים מסוג אחד בלבד עדיין מיוצגת והמדד האחר הוא אפס.

## Validation and Failure Semantics

Jobs של trips מקבלים `YYYY-MM`, ו־`station-daily` מקבל `YYYY-MM-DD`. Validation מתבצע לפני כל כתיבה.

קלט לא חוקי גורם להודעה ב־stderr, ל־exit code שאינו אפס, לאפס כתיבות ול־state זהה למצב שלפני ההרצה. Gold שמופעל לפני Silver אינו רשאי לייצר תשובה חלקית.

## Idempotency and Window Independence

כל job מחליף state רק בגרעין החלון שלו. הרצה חוזרת עם אותו input משאירה state זהה, וטעינת window חדש אינה משנה windows קיימים. הבדיקות משוות גם את התוכן ואת פלטי ה־JSON, ולא רק row counts.

## Output Boundary

`inspect` ו־`report` כותבים אובייקט JSON יחיד ל־stdout. כל log, diagnostic או error נכתב ל־stderr.

## Testing Strategy

הפיתוח מתבצע ב־TDD: בדיקה נכשלת, מימוש מינימלי, העברת הבדיקה ו־refactor.

Unit tests בודקות validation, סיווג market, parsing של XML, בחירת objects, קיבוץ exports וזיהוי schema באמצעות fixtures קטנים.

Integration tests בודקות PostgreSQL אמיתי, Bronze volume, transactions, window replacement, הפרדת jobs, פלט JSON ויכולת rebuild ללא אינטרנט.

## Reference Invariants

| Coordinate | Published | Conformed | Rejected |
|---|---:|---:|---:|
| `trips:jc 2019-06` | 39,430 | 39,430 | 0 |
| `trips:jc 2026-06` | 109,897 | 109,510 | 387 |
| `trips:nyc 2018-04` | 1,307,543 | 1,307,543 | 0 |

עבור `jc`, תחנה `JC115`, ביום `2026-06-02`, התוצאה היא 216 departures ו־209 arrivals.
