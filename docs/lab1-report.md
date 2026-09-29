# Лабораторна робота №1

**Тема:** Організація репозиторію ІС як сховища артефактів SDD. Git, гілки, конфлікт «людина – агент»
**Виконав:** Ілля Майстренко
**Індивідуальний проєкт (варіант 3):** Інформаційна система обліку витрат на харчування
**Кодинговий агент:** Claude Code
**Репозиторій:** https://github.com/d1aboli/food-expenses-is

## Мета

Навчитися організовувати репозиторій проєкту як єдине сховище артефактів SDD, використовувати Git для
версіювання специфікацій, документації та журналів роботи з агентом, розмежовувати зміни людини й агента
і вирішувати конфлікти, спираючись на специфікацію.

## 1. Структура репозиторію

```
food-expenses-is/
├── .gitignore
├── README.md          — про проєкт, структура, префікси комітів, гілки
├── spec/
│   └── idea.md        — початковий опис задуму + відкриті питання до ЛР2
├── src/               — код (поки порожньо, .gitkeep)
├── tests/             — тести (поки порожньо, .gitkeep)
├── docs/
│   └── lab1-report.md — цей звіт
└── logs/
    ├── agent.md       — запис про кодинговий агент
    └── conflict.md    — розбір конфлікту людина–агент і рішення GIT-GATE
```

## 2. Модель гілкування

Використовую простий GitHub Flow з короткими гілками. `main` — основна гілка.
Кожна зміна робиться в окремій гілці від `main`, переглядається через `git diff`
і зливається через `git merge --no-ff`, щоб в історії було видно злиття.

Назви гілок показують, звідки зміна:

- `docs/readme-rules` — документація;
- `agent/f4-periods` — зміна, згенерована кодинговим агентом;
- `human/f4-periods` — моя ручна зміна.

Гілки залишені у віддаленому репозиторії, щоб було видно приклад гілкування.

## 3. Конвенція комітів

`spec:` — ідея, вимоги; `test:` — тести; `feat:` — код; `docs:` — документація;
`log:` — записи в `logs/`; `gate:` — контрольна точка або злиття з вирішенням конфлікту;
`chore:` — службові зміни. Зміни агента позначаються `[agent]` у кінці повідомлення.

## 4. Використані команди Git

`git config`, `git init -b main`, `git status`, `git add`, `git rm --cached`, `git commit -m`, `git commit -am`,
`git remote add`, `git remote -v`, `git push -u origin`, `git push`, `git switch`, `git switch -c`,
`git diff`, `git diff --stat`, `git merge --no-ff`, `git log --oneline --graph --all`, `git fsck --full`,
`git fetch`, `git pull --no-rebase`.

## 5. Хід роботи

### 5.1 Налаштування Git і створення репозиторію

```
$ git config --global user.name "Ilya Maistrenko"
$ git config --global user.email "illmaistrenko@gmail.com"
$ git init -b main
Initialized empty Git repository in D:/study/4course/1sem/PIS/food-expenses-is/.git/
$ git add README.md .gitignore
$ git commit -m "chore: initial commit"
[main (root-commit) 8c5ba8b] chore: initial commit
 2 files changed, 12 insertions(+)
 create mode 100644 .gitignore
 create mode 100644 README.md
```

Зв'язування з GitHub:

```
$ git remote add origin https://github.com/d1aboli/food-expenses-is.git
$ git remote -v
origin  https://github.com/d1aboli/food-expenses-is.git (fetch)
origin  https://github.com/d1aboli/food-expenses-is.git (push)
$ git push -u origin main
To https://github.com/d1aboli/food-expenses-is.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

### 5.2 Структура SDD

```
$ git add .
$ git commit -m "chore: add SDD folders"
[main e59eb8b] chore: add SDD folders
 5 files changed, 0 insertions(+), 0 deletions(-)
 create mode 100644 docs/.gitkeep
 create mode 100644 logs/.gitkeep
 create mode 100644 spec/.gitkeep
 create mode 100644 src/.gitkeep
 create mode 100644 tests/.gitkeep
```

### 5.3 Опис задуму і запис про агента

```
$ git commit -m "spec: add system idea"
[main 874378b] spec: add system idea
 2 files changed, 29 insertions(+)
 delete mode 100644 spec/.gitkeep
 create mode 100644 spec/idea.md

$ git commit -m "log: add coding agent record"
[main 99e86d7] log: add coding agent record
 2 files changed, 24 insertions(+)
 delete mode 100644 logs/.gitkeep
 create mode 100644 logs/agent.md
```

У `logs/agent.md` описано: клас інструменту (кодинговий агент на основі LLM, працює з терміналу),
спосіб доступу (запускається в папці репозиторію, читає й редагує робочу копію, питає дозволу перед змінами)
і операції (аналіз структури, редагування файлів, `git status/diff/log`, коміти на запит).

### 5.4 Гілка, порівняння і злиття

```
$ git switch -c docs/readme-rules
$ git diff
@@ -4,3 +4,32 @@
+## Що де лежить
+- `spec/` — ідея системи, потім тут буде специфікація
...
$ git commit -m "docs: add structure and commit rules to README"
[docs/readme-rules 59293d9] docs: add structure and commit rules to README
 1 file changed, 29 insertions(+)
$ git switch main
$ git diff main docs/readme-rules --stat
 README.md | 29 +++++++++++++++++++++++++++++
 1 file changed, 29 insertions(+)
$ git merge --no-ff docs/readme-rules -m "Merge branch 'docs/readme-rules'"
Merge made by the 'ort' strategy.
 README.md | 29 +++++++++++++++++++++++++++++
 1 file changed, 29 insertions(+)
```

### 5.5 Зміна агента

Запит до агента: подивитися структуру репозиторію і `spec/idea.md`, знайти неоднозначне місце і внести одну
обґрунтовану зміну. Агент переглянув структуру, визначив, що єдиний артефакт вимог — `spec/idea.md`,
і що в F4 не визначено, як рахувати тиждень і місяць. Зміну я переглянув через `git diff` і тільки потім закомітив.

```
$ git switch -c agent/f4-periods
$ git diff spec/idea.md
@@ -16,7 +16,7 @@
 - F3. Переглянути список покупок.
-- F4. Переглянути загальні витрати за день, тиждень або місяць.
+- F4. Переглянути загальні витрати за період: сьогодні, останні 7 днів, останні 30 днів або за довільний діапазон дат — із розбивкою сум за категоріями.
$ git add spec/idea.md
$ git commit -m "spec: clarify F4 periods [agent]"
[agent/f4-periods 860bbff] spec: clarify F4 periods [agent]
 1 file changed, 1 insertion(+), 1 deletion(-)
$ git push -u origin agent/f4-periods
```

### 5.6 Паралельна ручна зміна

```
$ git switch main
$ git switch -c human/f4-periods
$ git diff spec/idea.md
-- F4. Переглянути загальні витрати за день, тиждень або місяць.
+- F4. Переглянути загальні витрати за календарний день, календарний тиждень (з понеділка по неділю) або календарний місяць.
$ git commit -am "spec: define F4 as calendar periods"
[human/f4-periods 14cd5c2] spec: define F4 as calendar periods
 1 file changed, 1 insertion(+), 1 deletion(-)
$ git push -u origin human/f4-periods
```

### 5.7 Злиття і конфлікт

```
$ git switch main
$ git merge --no-ff human/f4-periods -m "Merge branch 'human/f4-periods'"
Merge made by the 'ort' strategy.
 spec/idea.md | 2 +-
$ git merge --no-ff agent/f4-periods
Auto-merging spec/idea.md
CONFLICT (content): Merge conflict in spec/idea.md
Automatic merge failed; fix conflicts and then commit the result.
$ git status
Unmerged paths:
        both modified:   spec/idea.md
$ git diff
++<<<<<<< HEAD
 +- F4. Переглянути загальні витрати за календарний день, календарний тиждень (з понеділка по неділю) або календарний місяць.
++=======
+ - F4. Переглянути загальні витрати за період: сьогодні, останні 7 днів, останні 30 днів або за довільний діапазон дат — із розбивкою сум за категоріями.
++>>>>>>> agent/f4-periods
```

### 5.8 Вирішення конфлікту і перевірка цілісності

```
$ git add spec/idea.md logs/conflict.md
$ git commit -m "gate: resolve F4 conflict by system idea"
[main 52df81f] gate: resolve F4 conflict by system idea
$ git fsck --full
Checking ref database: 100% (1/1), done.
Checking object directories: 100% (256/256), done.
$ git status
On branch main
nothing to commit, working tree clean
```

Під час `git push` віддалений `main` уже містив мою правку README, зроблену через веб-інтерфейс GitHub,
тому спочатку підтягнув її:

```
$ git push
 ! [rejected]        main -> main (fetch first)
$ git pull --no-rebase
Merge made by the 'ort' strategy.
 README.md | 10 ----------
$ git push
   76007e3..5fc20e4  main -> main
```

## 6. Фрагмент історії комітів

```
*   5fc20e4 (HEAD -> main, origin/main) Merge branch 'main' of https://github.com/d1aboli/food-expenses-is
|\
| * 76007e3 Update README to simplify content
* |   52df81f gate: resolve F4 conflict by system idea
|\ \
| * | 860bbff (origin/agent/f4-periods, agent/f4-periods) spec: clarify F4 periods [agent]
* | |   90323fa Merge branch 'human/f4-periods'
|\ \ \
| |/ /
|/| |
| * | 14cd5c2 (origin/human/f4-periods, human/f4-periods) spec: define F4 as calendar periods
|/ /
* |   00fbe13 Merge branch 'docs/readme-rules'
|\ \
| * | 59293d9 (origin/docs/readme-rules, docs/readme-rules) docs: add structure and commit rules to README
|/ /
* 3465517 log: simplify agent record
* 99e86d7 log: add coding agent record
* 874378b spec: add system idea
* e59eb8b chore: add SDD folders
* 8c5ba8b chore: initial commit
```

## 7. Опис конфлікту

Від одного коміту створено дві гілки, які змінили той самий рядок F4 у `spec/idea.md`:

- **агент** (`860bbff`): «сьогодні, останні 7 днів, останні 30 днів або довільний діапазон дат — із розбивкою за категоріями»;
- **я** (`14cd5c2`): «календарний день, календарний тиждень (з понеділка по неділю) або календарний місяць».

Після злиття моєї гілки в `main` злиття гілки агента дало конфлікт змісту в `spec/idea.md`.

## 8. Обґрунтування рішення

Обидві версії звіряв не між собою, а з описом задуму в `spec/idea.md`:

- **день / тиждень / місяць** є в задумі — залишено;
- **як рахувати тиждень і місяць**: у задумі сказано, навіщо система — «не гадати в кінці місяця, куди все поділося».
  Отже, підсумок потрібен за календарний місяць (з 1-го по останнє число), а не за ковзні «останні 30 днів».
  Для узгодженості тиждень теж календарний — з понеділка по неділю (так прийнято в Україні й за ISO 8601);
- **довільний діапазон дат і суми за категоріями** (пропозиція агента) у задумі відсутні, а в обмеженнях
  аналітика прямо винесена за межі — відхилено.

Підсумковий рядок:

```
- F4. Переглянути загальні витрати за календарний день, календарний тиждень (з понеділка по неділю) або календарний місяць (з 1-го по останнє число).
```

Рішення не ґрунтується на тому, що зміна моя або що моя гілка злита першою: календарні періоди прийнято тому,
що вони відповідають меті, записаній у задумі.

Відсутню в задумі вимогу зафіксовано як відкрите питання до ЛР2 у `spec/idea.md`:
чи потрібні перегляд за довільний діапазон дат і суми за категоріями.

Повний запис рішення — `logs/conflict.md`.

## 9. Зміни людини і агента

**Кодинговий агент (Claude Code):**

- аналіз структури репозиторію і `spec/idea.md`;
- зміна рядка F4 у гілці `agent/f4-periods` (`860bbff`) — переглянута мною через `git diff` перед комітом.

**Я:**

- налаштування Git, створення локального і віддаленого репозиторію;
- структура SDD, `spec/idea.md`, `logs/agent.md`, README, конвенція комітів;
- ручна зміна F4 у гілці `human/f4-periods` (`14cd5c2`), правка README на GitHub (`76007e3`);
- усі злиття, розбір конфлікту, остаточний текст F4, відкрите питання, `logs/conflict.md`, push.

## 10. Контрольна точка GIT-GATE

**Пройдено.** Структура SDD створена, є опис задуму і запис про агента, продемонстровано коміти, гілки,
порівняння і злиття, конфлікт людина–агент вирішено за змістом задуму, відкрите питання передано в ЛР2,
`git fsck --full` без помилок, робоча копія чиста, усі гілки у віддаленому репозиторії.

## Висновки

Репозиторій зібрано як єдине місце для всіх артефактів SDD: ідеї, документації, журналів роботи з агентом.
Окремі гілки, позначка `[agent]` і записи в `logs/` дозволяють чітко бачити, що зробила людина, а що агент.
Зміну агента не можна приймати наосліп: у цьому випадку він, окрім корисного уточнення, додав функції,
яких немає в задумі, і це стало видно тільки через `git diff`. Конфлікт показав, що вирішувати його треба
за змістом затвердженого артефакту, а не за авторством чи порядком злиття.
