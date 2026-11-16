Шар REST API
============

Зовнішній шар системи. Відповідає за адреси, коди статусів і подання
даних; правил предметної області тут немає — вони в службах.

Усі маршрути оголошені під префіксом ``/api/v1``, як указано в розділі
``servers`` затвердженого контракту.

Застосунок
----------

.. automodule:: food_expenses.api.app

Залежності маршрутів
--------------------

.. automodule:: food_expenses.api.dependencies

Параметри шляху
---------------

.. automodule:: food_expenses.api.params

Схеми запитів і відповідей
--------------------------

.. automodule:: food_expenses.api.schemas

Обробка помилок
---------------

.. automodule:: food_expenses.api.error_handling

Маршрути: профілі
-----------------

.. automodule:: food_expenses.api.routers.profiles

Маршрути: категорії
-------------------

.. automodule:: food_expenses.api.routers.categories

Маршрути: покупки
-----------------

.. automodule:: food_expenses.api.routers.purchases

Маршрути: підсумки й графіки
----------------------------

.. automodule:: food_expenses.api.routers.summaries

Маршрути: бюджети
-----------------

.. automodule:: food_expenses.api.routers.budgets

Маршрути: резервні копії
------------------------

.. automodule:: food_expenses.api.routers.backups
