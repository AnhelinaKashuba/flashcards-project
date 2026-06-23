from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, get_flashed_messages
import sqlite3
import os
import json
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash  
from datetime import datetime, timedelta, date
import random
import secrets
from functools import wraps
from markupsafe import escape as _escape, Markup

app = Flask(__name__)
app.secret_key = "secret123"


def jinja_escape(value, strategy=None):
    if strategy is None or strategy == 'html':
        return _escape(value)
    if strategy == 'js':
        text = str(value)
        escaped = (
            text
            .replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\u2028', '\\u2028')
            .replace('\u2029', '\\u2029')
            .replace('</script>', '<\\/script>')
        )
        return Markup(escaped)
    raise ValueError(f"Unknown escape strategy: {strategy}")

app.jinja_env.filters['e'] = jinja_escape

DATABASE = "users.db"

translations = {
    "Головна": {"en": "Home", "es": "Inicio"},
    "Про сервіс": {"en": "About", "es": "Acerca"},
    "Як це працює?": {"en": "How it works?", "es": "¿Cómo funciona?"},
    "Увійти": {"en": "Login", "es": "Iniciar sesión"},
    "Реєстрація": {"en": "Register", "es": "Regístrate"},
    "Навчайтесь ефективно з <br>ออนไลน์-флешкартами": {"en": "Learn effectively with <br>online flashcards", "es": "Aprende eficazmente con <br>flashcards en línea"},
    "Створювайте власні навчальні набори, проходьте інтерактивні\n            тести та відслідковуйте свій прогрес": {"en": "Create your own study sets, take interactive tests and track your progress", "es": "Crea tus propios conjuntos de estudio, toma pruebas interactivas y sigue tu progreso"},
    "Реєстрація →": {"en": "Sign up →", "es": "Regístrate →"},
    "Вхід в акаунт": {"en": "Account login", "es": "Inicio de sesión"},
    "Email": {"en": "Email", "es": "Correo"},
    "Пароль": {"en": "Password", "es": "Contraseña"},
    "Створення акаунта": {"en": "Create account", "es": "Crear cuenta"},
    "Створення набору": {"en": "Create set", "es": "Crear conjunto"},
    "Назад до списку наборів": {"en": "Back to set list", "es": "Volver a la lista de conjuntos"},
    "Назва набору": {"en": "Set name", "es": "Nombre del conjunto"},
    "Додайте опис набору...": {"en": "Add set description...", "es": "Agrega descripción del conjunto..."},
    "Картки у цьому наборі": {"en": "Cards in this set", "es": "Tarjetas en este conjunto"},
    "Картка": {"en": "Card", "es": "Tarjeta"},
    "Термін": {"en": "Term", "es": "Término"},
    "Визначення": {"en": "Definition", "es": "Definición"},
    "Додати карту": {"en": "Add card", "es": "Agregar tarjeta"},
    "Зберегти набір": {"en": "Save set", "es": "Guardar conjunto"},
    "Ім’я користувача": {"en": "Username", "es": "Nombre de usuario"},
    "Навчайтесь ефективно з": {"en": "Learn effectively with", "es": "Aprende eficazmente con"},
    "онлайн-флешкартами": {"en": "online flashcards", "es": "flashcards en línea"},
    "Створюйте власні навчальні набори, проходьте інтерактивні тести та відслідковуйте свій прогрес": {"en": "Create your own study sets, take interactive tests and track your progress", "es": "Crea tus propios conjuntos de estudio, toma pruebas interactivas y sigue tu progreso"},
    "Підтвердіть пароль": {"en": "Confirm password", "es": "Confirmar contraseña"},
    "Мої набори": {"en": "My sets", "es": "Mis conjuntos"},
    "+ Створити новий набір": {"en": "+ Create new set", "es": "+ Crear nuevo conjunto"},
    "карток": {"en": "cards", "es": "tarjetas"},
    "Вивчено": {"en": "Learned", "es": "Aprendido"},
    "Додайте картки": {"en": "Add cards", "es": "Añade tarjetas"},
    "Видалити": {"en": "Delete", "es": "Eliminar"},
    "Редагувати": {"en": "Edit", "es": "Editar"},
    "Вивчати →": {"en": "Study →", "es": "Estudiar →"},
    "Темна тема": {"en": "Dark mode", "es": "Modo oscuro"},
    "Меню": {"en": "Menu", "es": "Menú"},
    "403 - Доступ заборонено": {"en": "403 - Forbidden", "es": "403 - Prohibido"},
    "404 - Сторінка не знайдена": {"en": "404 - Page not found", "es": "404 - Página no encontrada"},
    "Доступ заборонено": {"en": "Access forbidden", "es": "Acceso prohibido"},
    "У вас немає прав доступу до цього ресурсу. Перевірте, що ви маєте правильний доступ або спробуйте увійти іншим акаунтом.": {"en": "You do not have permission to access this resource. Check your access or try logging in with another account.", "es": "No tienes permiso para acceder a este recurso. Verifica tu acceso o intenta iniciar sesión con otra cuenta."},
    "На жаль, сторінка, яку ви шукаєте, не існує або була видалена.": {"en": "Sorry, the page you are looking for does not exist or has been removed.", "es": "Lo sentimos, la página que buscas no existe o ha sido eliminada."},
    "На головну": {"en": "Home", "es": "Inicio"},
    "Повернутися на головну": {"en": "Return to home", "es": "Volver al inicio"},
    "Пошук": {"en": "Search", "es": "Buscar"},
    "Всі": {"en": "All", "es": "Todos"},
    "Нові": {"en": "New", "es": "Nuevos"},
    "Вивчаю": {"en": "Learning", "es": "Aprendiendo"},
    "На повтор": {"en": "Due", "es": "Para repetir"},
    "Профіль": {"en": "Profile", "es": "Perfil"},
    "Мова сайту": {"en": "Site language", "es": "Idioma del sitio"},
    "Українська": {"en": "Ukrainian", "es": "Ucraniano"},
    "English": {"en": "English", "es": "Inglés"},
    "Español": {"en": "Spanish", "es": "Español"},
    "Зберегти зміни": {"en": "Save changes", "es": "Guardar cambios"},
    "Базові аватари": {"en": "Default avatars", "es": "Avatares predeterminados"},
    "Фото профілю": {"en": "Profile photo", "es": "Foto de perfil"},
    "Виберіть файл або оберіть базовий аватар": {"en": "Choose a file or pick a default avatar", "es": "Elige un archivo o elige un avatar predeterminado"},
    "Змінити пароль": {"en": "Change password", "es": "Cambiar contraseña"},
    "Поточний пароль": {"en": "Current password", "es": "Contraseña actual"},
    "Новий пароль": {"en": "New password", "es": "Nueva contraseña"},
    "Підтвердіть новий пароль": {"en": "Confirm new password", "es": "Confirmar nueva contraseña"},
    "Вийти": {"en": "Logout", "es": "Cerrar sesión"},
    "Вхід": {"en": "Login", "es": "Iniciar sesión"},
    "Немає акаунта?": {"en": "Don't have an account?", "es": "¿No tienes una cuenta?"},
    "Вже маєте акаунт?": {"en": "Already have an account?", "es": "¿Ya tienes una cuenta?"},
    "Вивчення": {"en": "Study", "es": "Estudio"},
    "Пошук карток...": {"en": "Search cards...", "es": "Buscar tarjetas..."},
    "Перемішати": {"en": "Shuffle", "es": "Mezclar"},
    "Список": {"en": "List", "es": "Lista"},
    "Прогрес:": {"en": "Progress:", "es": "Progreso:"},
    "Залишилось:": {"en": "Remaining:", "es": "Restante:"},
    "Картки": {"en": "Cards", "es": "Tarjetas"},
    "Quiz": {"en": "Quiz", "es": "Quiz"},
    "Вписати": {"en": "Write", "es": "Escribir"},
    "Вписуйте відповідь": {"en": "Enter the answer", "es": "Escribe la respuesta"},
    "Введіть відповідь...": {"en": "Enter the answer...", "es": "Escribe la respuesta..."},
    "Перевірити": {"en": "Check", "es": "Comprobar"},
    "Завантаження...": {"en": "Loading...", "es": "Cargando..."},
    "Натисніть, щоб перегорнути": {"en": "Click to flip", "es": "Haz clic para girar"},
    "Натисніть, щоб повернути": {"en": "Click to flip back", "es": "Haz clic para girar de nuevo"},
    "Нічого не вибрано.": {"en": "Nothing selected.", "es": "Nada seleccionado."},
    "Немає карток для колеса.": {"en": "No cards for the wheel.", "es": "No hay tarjetas para la rueda."},
    "Всі картки пройдено!": {"en": "All cards completed!", "es": "¡Todas las tarjetas completadas!"},
    "Правильно!": {"en": "Correct!", "es": "¡Correcto!"},
    "✅ Правильно!": {"en": "✅ Correct!", "es": "✅ ¡Correcto!"},
    "Неправильно. Спробуйте ще раз.": {"en": "Incorrect. Try again.", "es": "Incorrecto. Intenta de nuevo."},
    "❌ Неправильно. Правильна відповідь: ": {"en": "❌ Incorrect. Correct answer: ", "es": "❌ Incorrecto. Respuesta correcta: "},
    "✅ Правильна відповідь!": {"en": "✅ Correct answer!", "es": "✅ ¡Respuesta correcta!"},
    "❌ Неправильна відповідь!": {"en": "❌ Incorrect answer!", "es": "❌ ¡Respuesta incorrecta!"},
    "❌ Неправильно, спробуйте ще раз": {"en": "❌ Incorrect, try again", "es": "❌ Incorrecto, inténtalo de nuevo"},
    "🏆 Ви знайшли всі відповідності!": {"en": "🏆 You found all matches!", "es": "🏆 ¡Encontraste todas las coincidencias!"},
    "✅ Правильна пара!": {"en": "✅ Correct pair!", "es": "✅ ¡Par correcto!"},
    "📖 Ви забули цю картку. Спробуйте ще раз!": {"en": "📖 You forgot this card. Try again!", "es": "📖 Olvidaste esta tarjeta. ¡Intenta de nuevo!"},
    "📖 Ви вже вивчили цю картку!": {"en": "📖 You already learned this card!", "es": "📖 ¡Ya aprendiste esta tarjeta!"},
    "📖 Спробуйте запам'ятати цю картку": {"en": "📖 Try to remember this card", "es": "📖 Intenta recordar esta tarjeta"},
    "Результати тесту": {"en": "Quiz results", "es": "Resultados de la prueba"},
    "Результати": {"en": "Results", "es": "Resultados"},
    "Правильних відповідей": {"en": "Correct answers", "es": "Respuestas correctas"},
    "Відсоток": {"en": "Percentage", "es": "Porcentaje"},
    "Точність": {"en": "Accuracy", "es": "Precisión"},
    "Пройти тест ще раз": {"en": "Retake quiz", "es": "Volver a hacer la prueba"},
    "Повернутися до карток": {"en": "Return to cards", "es": "Volver a las tarjetas"},
    "Картка": {"en": "Card", "es": "Tarjeta"},
    "Попередній перегляд": {"en": "Preview", "es": "Vista previa"},
    "Обрано базовий аватар": {"en": "Default avatar selected", "es": "Avatar predeterminado seleccionado"},
    "Ви дійсно хочете видалити акаунт? Ця дія невідворотня.": {"en": "Are you sure you want to delete your account? This action is irreversible.", "es": "¿Estás seguro de que deseas eliminar tu cuenta? Esta acción es irreversible."},
    "Ви знаєте цю картку?": {"en": "Do you know this card?", "es": "¿Conoces esta tarjeta?"},
    "Знаю": {"en": "I know", "es": "Lo sé"},
    "Не знаю": {"en": "I don't know", "es": "No sé"},
    "Вітаємо!": {"en": "Congratulations!", "es": "¡Felicidades!"},
    "Ви переглянули всі картки в цьому наборі!": {"en": "You've reviewed all cards in this set!", "es": "¡Has revisado todas las tarjetas de este conjunto!"},
    "Вивчити незнайомі": {"en": "Study unknown ones", "es": "Estudiar desconocidos"},
    "Почати заново": {"en": "Start again", "es": "Empezar de nuevo"},
    "Повернутися до наборів": {"en": "Return to sets", "es": "Volver a conjuntos"},
    "Профіль користувача": {"en": "User profile", "es": "Perfil del usuario"},
    "Електронна адреса": {"en": "Email", "es": "Correo electrónico"},
    "Видалити обліковий запис": {"en": "Delete account", "es": "Eliminar cuenta"},
    "Назад": {"en": "Back", "es": "Atrás"},
    "Особливості": {"en": "Features", "es": "Características"},
    "Чому вибирати Flasho?": {"en": "Why choose Flasho?", "es": "¿Por qué elegir Flasho?"},
    "Легко створювати": {"en": "Easy to create", "es": "Fácil de crear"},
    "Швидко розробіть власні набори флешкарток за допомогою інтуїтивного редактора": {"en": "Quickly develop your own flashcard sets with an intuitive editor", "es": "Desarrolla rápidamente tus propios conjuntos de tarjetas con un editor intuitivo"},
    "Активне навчання": {"en": "Active learning", "es": "Aprendizaje activo"},
    "Інтерактивні вправи та випадкове відтворення для кращого засвоєння матеріалу": {"en": "Interactive exercises and random playback for better material retention", "es": "Ejercicios interactivos y reproducción aleatoria para una mejor retención de material"},
    "Відслідковуйте прогрес": {"en": "Track progress", "es": "Rastrear progreso"},
    "Детальна статистика навчання та графіки виконання для аналізу результатів": {"en": "Detailed study statistics and performance charts to analyze results", "es": "Estadísticas de estudio detalladas y gráficos de desempeño para analizar resultados"},
    "Будь-де і будь-коли": {"en": "Anywhere, anytime", "es": "En cualquier lugar, en cualquier momento"},
    "Мобільна оптимізація для навчання на ходу з будь-якого пристрою": {"en": "Mobile optimization to study on the go from any device", "es": "Optimización móvil para estudiar sobre la marcha desde cualquier dispositivo"},
    "Спільна робота": {"en": "Collaboration", "es": "Colaboración"},
    "Ділиться наборами з однокласниками та вчимось разом": {"en": "Share sets with classmates and learn together", "es": "Comparte conjuntos con compañeros y aprende juntos"},
    "Швидке вивчення": {"en": "Fast learning", "es": "Aprendizaje rápido"},
    "Оптимізовані алгоритми для максимальної ефективності навчання": {"en": "Optimized algorithms for maximum learning efficiency", "es": "Algoritmos optimizados para máxima eficiencia de aprendizaje"},
    "Активних користувачів": {"en": "Active users", "es": "Usuarios activos"},
    "Створених наборів": {"en": "Sets created", "es": "Conjuntos creados"},
    "Картконок вивчено": {"en": "Cards learned", "es": "Tarjetas aprendidas"},
    "Задоволеність користувачів": {"en": "User satisfaction", "es": "Satisfacción del usuario"},
    "Зареєструйтеся": {"en": "Sign up", "es": "Regístrate"},
    "Створіть вільний акаунт за допомогою електронної пошти": {"en": "Create a free account using email", "es": "Crea una cuenta gratuita usando correo electrónico"},
    "Створіть набір": {"en": "Create a set", "es": "Crear un conjunto"},
    "Додайте термін та визначення для кожної карточки": {"en": "Add term and definition for each card", "es": "Agrega término y definición para cada tarjeta"},
    "Навчайтеся": {"en": "Study", "es": "Estudiar"},
    "Використовуйте різні режими навчання: тест, вивчення, вибір": {"en": "Use different study modes: quiz, learn, flashcard", "es": "Usa diferentes modos de estudio: cuestionario, aprender, tarjeta"},
    "Відслідковуйте": {"en": "Track", "es": "Rastrear"},
    "Переглядайте статистику та аналізуйте свій прогрес": {"en": "View statistics and analyze your progress", "es": "Visualiza estadísticas y analiza tu progreso"},
    "Про Flasho": {"en": "About Flasho", "es": "Acerca de Flasho"},
    "Flasho - це сучасна платформа для ефективного навчання, розроблена спеціалістами в галузі освіти та технологій.": {"en": "Flasho is a modern learning platform developed by specialists in education and technology.", "es": "Flasho es una plataforma de aprendizaje moderna desarrollada por especialistas en educación y tecnología."},
    "Наша місія - зробити якісну освіту доступною для всіх, незалежно від місця проживання чи фінансових можливостей.": {"en": "Our mission is to make quality education accessible to all, regardless of location or financial capabilities.", "es": "Nuestra misión es hacer que la educación de calidad sea accesible para todos, independientemente de la ubicación o las capacidades financieras."},
    "З технологією адаптивного навчання та персоналізованими рекомендаціями, кожний користувач отримує оптимальний шлях до знань.": {"en": "With adaptive learning technology and personalized recommendations, each user gets an optimal path to knowledge.", "es": "Con tecnología de aprendizaje adaptativo y recomendaciones personalizadas, cada usuario obtiene un camino óptimo hacia el conocimiento."},
    "Безкоштовна реєстрація": {"en": "Free registration", "es": "Registro gratuito"},
    "Немає приховано платежів": {"en": "No hidden fees", "es": "Sin cargos ocultos"},
    "Підтримка багатьох мов": {"en": "Multi-language support", "es": "Compatibilidad con múltiples idiomas"},
    "Персональні дані захищені": {"en": "Personal data protected", "es": "Datos personales protegidos"},
    "Постійно розвиваємось": {"en": "Constantly evolving", "es": "Evolución constante"},
    "Готові почати навчання?": {"en": "Ready to start learning?", "es": "¿Listo para empezar a aprender?"},
    "Приєднайтеся до тисяч учнів, які вже вивчають ефективно": {"en": "Join thousands of students who are already learning effectively", "es": "Únete a miles de estudiantes que ya están aprendiendo de manera efectiva"},
    "Створити безкоштовний акаунт": {"en": "Create free account", "es": "Crear cuenta gratuita"},
    "Тема": {"en": "Theme", "es": "Tema"},
    "Довідка": {"en": "Help", "es": "Ayuda"},
    "Про програму": {"en": "About", "es": "Acerca de"},
    "Про сервіс": {"en": "About Service", "es": "Acerca del servicio"},
    "Статистика": {"en": "Statistics", "es": "Estadísticas"},
    "Видалити набір?": {"en": "Delete set?", "es": "¿Eliminar conjunto?"},
    "Нічого не знайдено": {"en": "Nothing found", "es": "Nada encontrado"},
    "Редагування набору": {"en": "Edit set", "es": "Editar conjunto"},
    "Опис": {"en": "Description", "es": "Descripción"},
    "Видалити картку": {"en": "Delete card", "es": "Eliminar tarjeta"},
    "Видалити фото": {"en": "Delete photo", "es": "Eliminar foto"},
    "Flasho": {"en": "Flasho", "es": "Flasho"},
    "Створити акаунт": {"en": "Create account", "es": "Crear cuenta"},
    "Зареєструватися": {"en": "Register", "es": "Registrarse"},
    "Стрічка днів": {"en": "Streak", "es": "Racha"},
    "Поточна серія днів": {"en": "Current streak", "es": "Racha actual"},
    "Набори": {"en": "Sets", "es": "Conjuntos"},
    "Всього наборів": {"en": "Total sets", "es": "Total de conjuntos"},
    "Карток": {"en": "Cards", "es": "Tarjetas"},
    "Всього карток": {"en": "Total cards", "es": "Total de tarjetas"},
    "Потрібно повторити": {"en": "Needs review", "es": "Necesita repaso"},
    "Карток для повторення сьогодні": {"en": "Cards to review today", "es": "Tarjetas para repasar hoy"},
    "Останні результати тестів": {"en": "Recent quiz results", "es": "Resultados recientes de pruebas"},
    "Набір": {"en": "Set", "es": "Conjunto"},
    "Результат": {"en": "Result", "es": "Resultado"},
    "Дата": {"en": "Date", "es": "Fecha"},
    "Тут з’являться результати ваших тестів після проходження quiz-режиму.": {"en": "Your quiz results will appear here after completing quiz mode.", "es": "Aquí aparecerán los resultados de tus pruebas después de completar el modo quiz."},
    "Вивчення набору": {"en": "Study set", "es": "Estudio del conjunto"},
    "Назад до наборів": {"en": "Back to sets", "es": "Volver a conjuntos"},
    "Вивчено:": {"en": "Learned:", "es": "Aprendido:"},
    "Тестування": {"en": "Testing", "es": "Evaluación"},
    "З'єднати": {"en": "Match", "es": "Emparejar"},
    "Колесо фортуни": {"en": "Fortune wheel", "es": "Rueda de la fortuna"},
    "Оберіть правильне визначення з варіантів нижче, щоб пройти тест.": {"en": "Choose the correct definition from the options below to take the test.", "es": "Elige la definición correcta de las opciones a continuación para realizar la prueba."},
    "Знайдіть відповідності": {"en": "Find matches", "es": "Encuentra coincidencias"},
    "Виберіть термін зліва, потім знайдіть правильне визначення справа.": {"en": "Select a term on the left, then find the correct definition on the right.", "es": "Selecciona un término a la izquierda y luego encuentra la definición correcta a la derecha."},
    "пари знайдено": {"en": "pairs found", "es": "pares encontrados"},
    "Натисніть «Крутити», щоб випадково обрати картку з набору.": {"en": "Press 'Spin' to randomly select a card from the set.", "es": "Pulsa 'Girar' para seleccionar una tarjeta al azar del conjunto."},
    "Крутити": {"en": "Spin", "es": "Girar"},
    "Оновити": {"en": "Refresh", "es": "Actualizar"},
    "Випадково обрана картка": {"en": "Randomly selected card", "es": "Tarjeta seleccionada al azar"},
    "Напишіть визначення": {"en": "Write the definition", "es": "Escribe la definición"},
    "Введіть визначення...": {"en": "Enter the definition...", "es": "Introduce la definición..."},
    "Скасувати": {"en": "Cancel", "es": "Cancelar"},
    "Впишіть правильну відповідь": {"en": "Enter the correct answer", "es": "Escribe la respuesta correcta"},
    "Уважно прочитайте термін і впишіть правильне визначення нижче.": {"en": "Read the term carefully and enter the correct definition below.", "es": "Lee el término con atención y escribe la definición correcta a continuación."},
    "Введіть відповідь перед перевіркою.": {"en": "Enter the answer before checking.", "es": "Introduce la respuesta antes de comprobar."},
    "Правильно!": {"en": "Correct!", "es": "¡Correcto!"},
    "Неправильно. Спробуйте ще раз.": {"en": "Incorrect. Try again.", "es": "Incorrecto. Intenta de nuevo."},
    "Терміни": {"en": "Terms", "es": "Términos"},
    "Немає карток для відображення.": {"en": "No cards to display.", "es": "No hay tarjetas para mostrar."},
    "Не вивчено": {"en": "Not learned", "es": "No aprendido"},
    "Вітаємо! Ви вивчили всі картки!": {"en": "Congratulations! You have learned all cards!", "es": "¡Felicidades! Has aprendido todas las tarjetas!"},
    "Додати картки": {"en": "Add cards", "es": "Agregar tarjetas"},
    "Завантажити зображення визначення": {"en": "Upload definition image", "es": "Cargar imagen de definición"},
    "Завантажити зображення терміну": {"en": "Upload term image", "es": "Cargar imagen del término"},
    "Залишилось вивчити:": {"en": "Remaining to study:", "es": "Queda por estudiar:"},
    "Неправильно!": {"en": "Incorrect!", "es": "¡Incorrecto!"},
    "Правильна відповідь:": {"en": "Correct answer:", "es": "Respuesta correcta:"},
    "Сторінка не знайдена": {"en": "Page not found", "es": "Página no encontrada"},
    "Твоя відповідь:": {"en": "Your answer:", "es": "Tu respuesta:"},
    "У цьому наборі немає карток. Додайте картки, щоб почати вивчення.": {"en": "There are no cards in this set. Add cards to start studying.", "es": "No hay cartas en este conjunto. Agrega tarjetas para comenzar a estudiar."},
    "карток вивчено": {"en": "cards learned", "es": "tarjetas aprendidas"},
    "✅ Ви вже вивчили цю картку!": {"en": "✅ You have already learned this card!", "es": "✅ ¡Ya has aprendido esta tarjeta!"},
    "✅ Чудово! Картку вивчено!": {"en": "✅ Great! Card learned!", "es": "✅ ¡Genial! ¡Tarjeta aprendida!"},
    "🔀 Картки перемішано!": {"en": "🔀 Cards shuffled!", "es": "🔀 ¡Tarjetas mezcladas!"}
}

def translate_text(text):
    lang = session.get("language", "uk")
    if lang == "uk":
        return text
    return translations.get(text, {}).get(lang, text)


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]

@app.before_request
def protect_csrf():
    if request.method == "POST" and not request.path.startswith("/api/"):
        token = session.get("csrf_token")
        form_token = request.form.get("csrf_token")
        if not token or not form_token or token != form_token:
            flash("Недійсний CSRF токен.", "danger")
            return redirect(request.referrer or url_for("index"))

@app.context_processor
def inject_language():
    return {
        "_": translate_text,
        "lang": session.get("language", "uk"),
        "csrf_token": generate_csrf_token()
    }

# ==================== УТИЛІТНІ ФУНКЦІЇ ====================

def login_required(f):
    """Декоратор для перевірки авторизації користувача"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Будь ласка, увійдіть в систему", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_user_or_404():
    """Отримати поточного користувача або повернути None"""
    if "user_id" not in session:
        return None
    try:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        if not user:
            session.clear()
            return None
        return user
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return None

def get_user_set_or_404(set_id):
    """Отримати набір користувача або повернути None з повідомленням про помилку"""
    try:
        conn = get_db()
        set_data = conn.execute(
            "SELECT * FROM sets WHERE id=? AND user_id=?", 
            (set_id, session.get("user_id"))
        ).fetchone()
        conn.close()
        if not set_data:
            return None
        return set_data
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return None

def validate_username(username):
    """Валідація імені користувача"""
    if not username or len(username) < 2:
        return "Ім'я користувача має бути не менше 2 символів", False
    if len(username) > 50:
        return "Ім'я користувача не може перевищувати 50 символів", False
    if not all(c.isalnum() or c in '-_' for c in username):
        return "Ім'я користувача може містити тільки букви, цифри, дефіси та підкреслення", False
    return "", True

def validate_password(password):
    """Валідація пароля"""
    if not password or len(password) < 6:
        return "Пароль має бути не менше 6 символів", False
    if len(password) > 100:
        return "Пароль не може перевищувати 100 символів", False
    return "", True

def validate_email(email):
    """Валідація email"""
    if not email or len(email) < 5 or '@' not in email:
        return "Введіть коректну email адресу", False
    if len(email) > 100:
        return "Email не може перевищувати 100 символів", False
    return "", True

def validate_set_name(name):
    """Валідація назви набору"""
    if not name or len(name.strip()) == 0:
        return "Назва набору не може бути пустою", False
    if len(name) > 200:
        return "Назва набору не може перевищувати 200 символів", False
    return "", True

# ==================== ПОМИЛКИ ====================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403

@app.errorhandler(500)
def internal_error(error):
    flash("Помилка сервера. Спробуйте пізніше", "danger")
    return redirect(url_for("dashboard") if "user_id" in session else url_for("index"))


UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Підключення до бази
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30, check_same_thread=False)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute('PRAGMA busy_timeout=30000')
    except sqlite3.OperationalError:
        pass
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    # Таблиця users
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        avatar TEXT
    )
    """)
    
    # ДОДАТИ - таблиця наборів
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        created_date TEXT DEFAULT CURRENT_DATE,
        cards_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    
    # ДОДАТИ - таблиця карток
    conn.execute("""
    CREATE TABLE IF NOT EXISTS cards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id INTEGER NOT NULL,
        term TEXT NOT NULL,
        definition TEXT NOT NULL,
        FOREIGN KEY (set_id) REFERENCES sets (id)
    )
    """)
    
    # ДОДАТИ - таблиця прогресу з spaced repetition
    conn.execute("""
    CREATE TABLE IF NOT EXISTS progress(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        card_id INTEGER NOT NULL,
        learned BOOLEAN DEFAULT 0,
        interval INTEGER DEFAULT 1,
        ease_factor REAL DEFAULT 2.5,
        next_review TEXT,
        UNIQUE(user_id, card_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (card_id) REFERENCES cards (id)
    )
    """)
    
    # ДОДАТИ - таблиця статистики користувача
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_stats(
        user_id INTEGER PRIMARY KEY,
        streak INTEGER DEFAULT 0,
        last_study TEXT,
        total_learned INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS test_results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        set_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        passed INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (set_id) REFERENCES sets (id)
    )
    """)
    
    # Оновлюємо існуючу таблицю progress новими колонками (якщо вони не існують)
    try:
        conn.execute("ALTER TABLE progress ADD COLUMN interval INTEGER DEFAULT 1")
    except:
        pass
    try:
        conn.execute("ALTER TABLE progress ADD COLUMN ease_factor REAL DEFAULT 2.5")
    except:
        pass
    try:
        conn.execute("ALTER TABLE progress ADD COLUMN next_review TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE cards ADD COLUMN term_image TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE cards ADD COLUMN definition_image TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uk'")
    except:
        pass
    
    conn.commit()
    conn.close()
    

# Викликати нову функцію
create_tables()  # замість create_table()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, prefix=""):
    """
    Безпечне завантаження файлу з валідацією та обробкою помилок
    Args:
        file: Werkzeug FileStorage object
        prefix: префікс для назви файлу (напр. 'user_123')
    Returns:
        filename якщо успішно, None якщо помилка
    """
    if not file or not file.filename:
        return None
    
    if not allowed_file(file.filename):
        return None
    
    try:
        # Перевірка розміру файлу
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > MAX_FILE_SIZE:
            return None
        
        # Генерація безпечної назви файлу
        ext = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{prefix}_{timestamp}" if prefix else timestamp
        filename = secure_filename(f"{base_filename}.{ext}")
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Уникнення перезапису існуючих файлів
        counter = 1
        while os.path.exists(filepath):
            name_parts = filename.rsplit('.', 1)
            filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
        
        file.save(filepath)
        return filename
    except Exception as e:
        return None


def update_spaced_repetition(progress, quality):
    interval = progress["interval"] or 1
    ease = progress["ease_factor"] or 2.5

    if quality < 3:
        interval = 1
    else:
        interval = int(interval * ease)
        ease = max(1.3, ease + (0.1 - (5 - quality)*(0.08 + (5 - quality)*0.02)))

    next_review = datetime.now() + timedelta(days=interval)

    return interval, ease, next_review.strftime("%Y-%m-%d")

def update_streak(user_id, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    today = date.today().isoformat()

    stats = conn.execute(
        "SELECT * FROM user_stats WHERE user_id=?", (user_id,)
    ).fetchone()

    if not stats:
        conn.execute(
            "INSERT INTO user_stats (user_id, streak, last_study) VALUES (?,1,?)",
            (user_id, today)
        )
    else:
        if stats["last_study"] == today:
            if close_conn:
                conn.close()
            return
        elif stats["last_study"] == (date.today() - timedelta(days=1)).isoformat():
            conn.execute(
                "UPDATE user_stats SET streak = streak + 1, last_study=? WHERE user_id=?",
                (today, user_id)
            )
        else:
            conn.execute(
                "UPDATE user_stats SET streak = 1, last_study=? WHERE user_id=?",
                (today, user_id)
            )

    if close_conn:
        conn.commit()
        conn.close()

@app.route("/")
def index():
    # Обробка параметра мови з URL
    lang = request.args.get("lang")
    if lang and lang in ["uk", "en", "es"]:
        session["language"] = lang
    return render_template("index.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        conn = get_db()
        # ЗМІНИТИ - спочатку знайти користувача за email
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()
        
        # ЗМІНИТИ - перевірити пароль
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["avatar"] = user["avatar"]
            session["language"] = user["language"] if "language" in user.keys() and user["language"] else "uk"
            return redirect(url_for("dashboard"))
        else:
            flash("Невірний email або пароль.", "danger")
    
    return render_template("login.html")



# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password")

        if not username or not email or not password:
            flash("Заповніть всі потрібні поля.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Паролі не співпадають.", "danger")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)
        
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username,email,password,language) VALUES (?,?,?,?)",
                (username, email, hashed_password, "uk")
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email вже використовується або ім'я користувача зайняте.", "danger")
            conn.close()
            return render_template("register.html")
        
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()
        conn.close()
        
        # Додати avatar і мову в сесію
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["avatar"] = user["avatar"]
        session["language"] = user["language"] if "language" in user.keys() and user["language"] else "uk"
        
        return redirect(url_for("dashboard"))
    
    return render_template("register.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user_or_404()
    if not user:
        return redirect(url_for("login"))
    
    search_query = request.args.get("search", "").strip()
    filter_type = request.args.get("filter", "all")  # all, new, learning, due
    
    try:
        conn = get_db()
        
        # Базовий запит
        query = """
            SELECT s.*, 
                   COUNT(c.id) as cards_count,
                   COUNT(CASE WHEN p.learned = 1 THEN 1 END) as learned_cards,
                   COUNT(CASE WHEN p.next_review IS NOT NULL AND p.next_review <= date('now') THEN 1 END) as due_cards
            FROM sets s
            LEFT JOIN cards c ON s.id = c.set_id
            LEFT JOIN progress p ON c.id = p.card_id AND p.user_id = ?
            WHERE s.user_id = ?
            GROUP BY s.id
        """
        params = [session["user_id"], session["user_id"]]
        
        # Фільтр за пошуком
        if search_query:
            query += " HAVING s.name LIKE ?"
            params.append(f"%{search_query}%")
        
        query += " ORDER BY s.created_date DESC"
        
        sets = conn.execute(query, params).fetchall()
        
        # Фільтрація за типом
        if filter_type == "new":
            sets = [s for s in sets if s["learned_cards"] == 0]
        elif filter_type == "learning":
            sets = [s for s in sets if 0 < s["learned_cards"] < s["cards_count"]]
        elif filter_type == "due":
            sets = [s for s in sets if s["due_cards"] > 0]
        
        conn.close()
        
        return render_template("dashboard.html", 
                             username=session["username"],
                             user=user,
                             sets=sets,
                             search_query=search_query,
                             filter_type=filter_type)
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("index"))



# ---------------- PROFILE ----------------

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    user = get_user_or_404()
    if not user:
        return redirect(url_for("login"))
    
    try:
        conn = get_db()
        
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "delete_account":
                conn.execute("DELETE FROM progress WHERE user_id=?", (session["user_id"],))
                conn.execute("DELETE FROM test_results WHERE user_id=?", (session["user_id"],))
                conn.execute("DELETE FROM user_stats WHERE user_id=?", (session["user_id"],))
                sets = conn.execute("SELECT id FROM sets WHERE user_id=?", (session["user_id"],)).fetchall()
                for s in sets:
                    conn.execute("DELETE FROM cards WHERE set_id=?", (s["id"],))
                conn.execute("DELETE FROM sets WHERE user_id=?", (session["user_id"],))
                conn.execute("DELETE FROM users WHERE id=?", (session["user_id"],))
                conn.commit()
                conn.close()
                session.clear()
                flash("Акаунт успішно видалено.", "success")
                return redirect(url_for("index"))

            if action == "change_password":
                current_password = request.form.get("current_password", "").strip()
                new_password = request.form.get("new_password", "").strip()
                confirm_password = request.form.get("confirm_password", "").strip()

                if not current_password or not new_password or not confirm_password:
                    flash("Заповніть всі поля для зміни пароля.", "danger")
                elif new_password != confirm_password:
                    flash("Новий пароль та підтвердження не співпадають.", "danger")
                elif not check_password_hash(user["password"], current_password):
                    flash("Поточний пароль невірний.", "danger")
                else:
                    err_msg, is_valid = validate_password(new_password)
                    if not is_valid:
                        flash(err_msg, "danger")
                    else:
                        hashed_password = generate_password_hash(new_password)
                        conn.execute(
                            "UPDATE users SET password=? WHERE id=?",
                            (hashed_password, session["user_id"])
                        )
                        conn.commit()
                        flash("Пароль успішно змінено.", "success")
                        conn.close()
                        return redirect(url_for("profile"))
            else:
                username = request.form.get("username", "").strip()
                language = request.form.get("language", "uk")
                avatar_choice = request.form.get("avatar_choice", "")
                avatar_file = request.files.get("avatar", None)
                
                has_changes = False

                # Зміна імені користувача
                if username and username != session["username"]:
                    err_msg, is_valid = validate_username(username)
                    if not is_valid:
                        flash(err_msg, "danger")
                    else:
                        existing = conn.execute(
                            "SELECT id FROM users WHERE username=? AND id!=?",
                            (username, session["user_id"])
                        ).fetchone()
                        if existing:
                            flash("Ім'я користувача вже зайняте.", "danger")
                        else:
                            conn.execute(
                                "UPDATE users SET username=? WHERE id=?",
                                (username, session["user_id"])
                            )
                            session["username"] = username
                            flash("Ім'я користувача оновлено.", "success")
                            has_changes = True

                # Завантаження аватара
                if avatar_file and avatar_file.filename:
                    uploaded = save_uploaded_file(avatar_file, prefix=f"user_{session['user_id']}")
                    if uploaded:
                        conn.execute(
                            "UPDATE users SET avatar=? WHERE id=?",
                            (uploaded, session["user_id"])
                        )
                        session["avatar"] = uploaded
                        flash("Аватар оновлено.", "success")
                        has_changes = True
                    else:
                        flash("Невалідний файл аватара або занадто великий.", "danger")
                elif avatar_choice:
                    conn.execute(
                        "UPDATE users SET avatar=? WHERE id=?",
                        (f"default_{avatar_choice}", session["user_id"])
                    )
                    session["avatar"] = f"default_{avatar_choice}"
                    flash("Обрано базовий аватар.", "success")
                    has_changes = True

                # Зміна мови
                current_language = user["language"] if user["language"] else "uk"
                if language and language != current_language and language in ["uk", "en", "es"]:
                    conn.execute(
                        "UPDATE users SET language=? WHERE id=?",
                        (language, session["user_id"])
                    )
                    session["language"] = language
                    flash("Мову сайту оновлено.", "success")
                    has_changes = True

                if has_changes:
                    conn.commit()
                    flash("Зміни збережено.", "success")
                else:
                    flash("Немає змін для збереження.", "info")

                conn.close()
                return redirect(url_for("profile"))
        
        conn.close()
        return render_template("profile.html", user=user)
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("dashboard"))



@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))



# ДОДАТИ - створення набору
@app.route("/create_set", methods=["GET","POST"])
@login_required
def create_set():
    user = get_user_or_404()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            user_id = session["user_id"]
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            terms = request.form.getlist("term[]")
            definitions = request.form.getlist("definition[]")
            term_images = request.files.getlist("term_image[]")
            definition_images = request.files.getlist("definition_image[]")

            # Валідація назви набору
            err_msg, is_valid = validate_set_name(name)
            if not is_valid:
                flash(err_msg, "danger")
                return render_template("create_set.html", user=user)

            # Перевірка наявності карток
            if not terms or not definitions:
                flash("Додайте хоча б одну картку", "danger")
                return render_template("create_set.html", user=user)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO sets (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, name, description)
            )

            set_id = cursor.lastrowid
            cards_added = 0

            for idx, (term, definition) in enumerate(zip(terms, definitions)):
                term = term.strip()
                definition = definition.strip()
                term_image = None
                definition_image = None

                if idx < len(term_images) and term_images[idx].filename:
                    uploaded = save_uploaded_file(term_images[idx], prefix=f"term_{set_id}_{idx}")
                    if uploaded:
                        term_image = uploaded
                        
                if idx < len(definition_images) and definition_images[idx].filename:
                    uploaded = save_uploaded_file(definition_images[idx], prefix=f"def_{set_id}_{idx}")
                    if uploaded:
                        definition_image = uploaded

                if term or definition or term_image or definition_image:
                    cursor.execute(
                        "INSERT INTO cards (set_id, term, definition, term_image, definition_image) VALUES (?,?,?,?,?)",
                        (set_id, term, definition, term_image, definition_image)
                    )
                    cards_added += 1
            
            cursor.execute(
                "UPDATE sets SET cards_count = ? WHERE id = ?",
                (cards_added, set_id)
            )

            conn.commit()
            conn.close()

            flash(f"Набір успішно створено! Додано {cards_added} карток", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.Error as e:
            flash(f"Помилка бази даних: {str(e)}", "danger")
            return render_template("create_set.html")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    
    return render_template("create_set.html", user=user)

# ДОДАТИ - редагування набору
@app.route("/set/<int:set_id>/edit", methods=["GET", "POST"])
@login_required
def edit_set(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        
        if not set_data:
            flash("Набір не знайдено або у вас немає доступу", "danger")
            return redirect(url_for("dashboard"))
        
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            terms = request.form.getlist("term[]")
            definitions = request.form.getlist("definition[]")
            term_images = request.files.getlist("term_image[]")
            definition_images = request.files.getlist("definition_image[]")
            existing_term_images = request.form.getlist("existing_term_image[]")
            existing_definition_images = request.form.getlist("existing_definition_image[]")
            
            # Валідація
            err_msg, is_valid = validate_set_name(name)
            if not is_valid:
                flash(err_msg, "danger")
                conn = get_db()
                cards = conn.execute("SELECT * FROM cards WHERE set_id=?", (set_id,)).fetchall()
                user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
                conn.close()
                return render_template("edit_set.html", set=set_data, cards=cards, user=user)
            
            conn = get_db()
            conn.execute(
                "UPDATE sets SET name=?, description=? WHERE id=?",
                (name, description, set_id)
            )
            
            conn.execute("DELETE FROM cards WHERE set_id=?", (set_id,))
            
            added = 0
            for idx, (term, definition) in enumerate(zip(terms, definitions)):
                term = term.strip()
                definition = definition.strip()
                term_image = existing_term_images[idx] if idx < len(existing_term_images) else None
                definition_image = existing_definition_images[idx] if idx < len(existing_definition_images) else None
                
                if idx < len(term_images) and term_images[idx].filename:
                    uploaded = save_uploaded_file(term_images[idx], prefix=f"term_{set_id}_{idx}")
                    if uploaded:
                        term_image = uploaded
                        
                if idx < len(definition_images) and definition_images[idx].filename:
                    uploaded = save_uploaded_file(definition_images[idx], prefix=f"def_{set_id}_{idx}")
                    if uploaded:
                        definition_image = uploaded
                        
                if term or definition or term_image or definition_image:
                    conn.execute(
                        "INSERT INTO cards (set_id, term, definition, term_image, definition_image) VALUES (?,?,?,?,?)",
                        (set_id, term, definition, term_image, definition_image)
                    )
                    added += 1
            
            conn.execute(
                "UPDATE sets SET cards_count = ? WHERE id = ?",
                (added, set_id)
            )
            
            conn.commit()
            conn.close()
            
            flash(f"Набір успішно оновлено! Додано {added} карток", "success")
            return redirect(url_for("dashboard"))
        
        conn = get_db()
        cards = conn.execute(
            "SELECT * FROM cards WHERE set_id=?", (set_id,)
        ).fetchall()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        
        return render_template("edit_set.html", set=set_data, cards=cards, user=user)
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

# ДОДАТИ - видалення набору
@app.route("/set/<int:set_id>/delete", methods=["POST"])
@login_required
def delete_set(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        
        if not set_data:
            flash("Набір не знайдено", "danger")
            return redirect(url_for("dashboard"))
        
        conn = get_db()
        
        conn.execute("DELETE FROM progress WHERE card_id IN (SELECT id FROM cards WHERE set_id=?)", (set_id,))
        conn.execute("DELETE FROM cards WHERE set_id=?", (set_id,))
        conn.execute("DELETE FROM sets WHERE id=? AND user_id=?", (set_id, session["user_id"]))
        
        conn.commit()
        conn.close()
        
        flash("Набір видалено", "success")
        return redirect(url_for("dashboard"))
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("dashboard"))



@app.route("/statistics")
@login_required
def statistics():
    try:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        stats = conn.execute("SELECT * FROM user_stats WHERE user_id=?", (session["user_id"],)).fetchone()
        total_sets = conn.execute("SELECT COUNT(*) as count FROM sets WHERE user_id=?", (session["user_id"],)).fetchone()["count"]
        total_cards = conn.execute(
            "SELECT COUNT(*) as count FROM cards WHERE set_id IN (SELECT id FROM sets WHERE user_id=?)", 
            (session["user_id"],)
        ).fetchone()["count"]
        due_review = conn.execute(
            "SELECT COUNT(DISTINCT p.card_id) as count FROM progress p WHERE p.user_id=? AND (p.next_review IS NULL OR p.next_review <= date('now'))", 
            (session["user_id"],)
        ).fetchone()["count"]
        recent_results = conn.execute(
            "SELECT tr.*, s.name as set_name FROM test_results tr LEFT JOIN sets s ON tr.set_id=s.id WHERE tr.user_id=? ORDER BY tr.created_at DESC LIMIT 8",
            (session["user_id"],)
        ).fetchall()
        conn.close()

        return render_template("statistics.html", 
                             user=user, 
                             stats=stats, 
                             total_sets=total_sets, 
                             total_cards=total_cards, 
                             due_review=due_review, 
                             recent_results=recent_results)
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

@app.route("/api/save_quiz_result/<int:set_id>", methods=["POST"])
@login_required
def save_quiz_result(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        if not set_data:
            return jsonify({"error": "Set not found"}), 404

        data = request.get_json() or {}
        score = int(data.get("score", 0))
        total = int(data.get("total", 0))
        passed = 1 if total > 0 and (score / total) >= 0.6 else 0

        conn = get_db()
        conn.execute(
            "INSERT INTO test_results (user_id, set_id, score, total, passed) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], set_id, score, total, passed)
        )
        
        # Оновлення streak
        update_streak(session["user_id"], conn)
        
        conn.commit()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API для отримання карток
@app.route("/api/get_cards/<int:set_id>")
@login_required
def get_cards(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        
        if not set_data:
            return jsonify({"error": "Set not found"}), 404
        
        conn = get_db()
        
        # Отримуємо картки
        cards = conn.execute(
            "SELECT id, term, definition, term_image, definition_image FROM cards WHERE set_id=?", 
            (set_id,)
        ).fetchall()
        
        # Отримуємо прогрес - тільки картки які потрібно повторити або не вивчені
        progress = conn.execute(
            """SELECT card_id, learned, next_review FROM progress 
               WHERE user_id=? AND card_id IN (SELECT id FROM cards WHERE set_id=?)
               AND (next_review IS NULL OR next_review <= date('now') OR learned=0)""",
            (session["user_id"], set_id)
        ).fetchall()
        
        conn.close()
        
        cards_list = [{
            "id": card["id"],
            "term": card["term"],
            "definition": card["definition"],
            "term_image": card["term_image"],
            "definition_image": card["definition_image"]
        } for card in cards]
        progress_dict = {str(p["card_id"]): {
            "status": "learned" if p["learned"] else "not_learned",
            "next_review": p["next_review"]
        } for p in progress}
        
        return jsonify({
            "cards": cards_list,
            "progress": progress_dict,
            "set_name": set_data["name"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API для збереження прогресу
@app.route("/api/save_progress/<int:set_id>", methods=["POST"])
@login_required
def save_progress(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        if not set_data:
            return jsonify({"error": "Set not found"}), 404
        
        data = request.get_json()
        card_id = data.get("card_id")
        learned = data.get("learned", False)
        
        if not card_id:
            return jsonify({"error": "Invalid card_id"}), 400
        
        quality = 5 if learned else 2
        
        conn = get_db()
        
        # Перевіряємо чи існує запис прогресу
        existing = conn.execute(
            "SELECT * FROM progress WHERE user_id=? AND card_id=?",
            (session["user_id"], card_id)
        ).fetchone()
        
        if existing:
            interval, ease, next_review = update_spaced_repetition(existing, quality)

            conn.execute("""
                UPDATE progress 
                SET learned=?, interval=?, ease_factor=?, next_review=?
                WHERE user_id=? AND card_id=?
            """, (1 if learned else 0, interval, ease, next_review,
                  session["user_id"], card_id))
        else:
            interval, ease, next_review = update_spaced_repetition(
                {"interval": 1, "ease_factor": 2.5}, 
                quality
            )
            conn.execute(
                "INSERT INTO progress (user_id, card_id, learned, interval, ease_factor, next_review) VALUES (?, ?, ?, ?, ?, ?)",
                (session["user_id"], card_id, 1 if learned else 0, interval, ease, next_review)
            )
        
        # Оновлюємо streak
        update_streak(session["user_id"], conn)
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Оновлений маршрут для сторінки вивчення
@app.route("/set/<int:set_id>/study")
@login_required
def study_set(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        
        if not set_data:
            flash("Набір не знайдено", "danger")
            return redirect(url_for("dashboard"))
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        
        return render_template("study.html", set_id=set_id, set_name=set_data["name"], user=user)
    except sqlite3.Error as e:
        flash(f"Помилка бази даних: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

# API для quiz mode
@app.route("/api/quiz/<int:set_id>")
@login_required
def quiz(set_id):
    try:
        set_data = get_user_set_or_404(set_id)
        if not set_data:
            return jsonify({"error": "Set not found"}), 404
        
        conn = get_db()

        cards = conn.execute(
            "SELECT * FROM cards WHERE set_id=?",
            (set_id,)
        ).fetchall()
        
        conn.close()

        if len(cards) < 4:
            return jsonify({"error": "Not enough cards for quiz"})

        card = random.choice(cards)
        options = random.sample(cards, min(4, len(cards)))

        return jsonify({
            "question": card["term"],
            "correct": card["definition"],
            "options": [c["definition"] for c in options]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API для отримання streak
@app.route("/api/get_streak")
@login_required
def get_streak():
    try:
        conn = get_db()
        stats = conn.execute(
            "SELECT streak FROM user_stats WHERE user_id=?", (session["user_id"],)
        ).fetchone()
        conn.close()
        
        return jsonify({"streak": stats["streak"] if stats else 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)