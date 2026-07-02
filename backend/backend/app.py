# ============================================
# Srunington Backend — Flask API
# ============================================

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import os
import json

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с GitHub Pages

# Путь к базе данных
DB_PATH = 'srunington.db'

# ============================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================
def init_db():
    """Создаёт таблицы при первом запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица сообщений чата
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            author TEXT NOT NULL,
            author_avatar TEXT,
            text TEXT NOT NULL,
            time TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_edited INTEGER DEFAULT 0,
            reply_to_id TEXT,
            reply_to_author TEXT,
            reply_to_text TEXT,
            reply_to_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица зарегистрированных игроков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица голосов за MVP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mvp_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date TEXT NOT NULL,
            voter_device_id TEXT NOT NULL,
            voter_name TEXT NOT NULL,
            voted_for TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(match_date, voter_device_id)
        )
    ''')
    
    # Таблица текущего MVP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mvp_current (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            player_name TEXT NOT NULL,
            streak INTEGER DEFAULT 1,
            match_date TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица настроек матча
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            match_date TEXT NOT NULL,
            match_time TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица кодов админа
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_codes (
            code TEXT PRIMARY KEY,
            is_used INTEGER DEFAULT 0,
            used_by_device TEXT,
            used_at TIMESTAMP
        )
    ''')
    
    # Таблица админов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            device_id TEXT PRIMARY KEY,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем начальные данные, если их нет
    cursor.execute('SELECT COUNT(*) FROM match_settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO match_settings (id, match_date, match_time) VALUES (1, ?, ?)',
            ('2026-06-15', '19:30')
        )
    
    # Добавляем начальные коды админа
    cursor.execute('SELECT COUNT(*) FROM admin_codes')
    if cursor.fetchone()[0] == 0:
        initial_codes = [
            'SRUN-7A3K', 'SRUN-9M2P', 'SRUN-4B8N', 'SRUN-6T1Q', 'SRUN-2R5W',
            'SRUN-8H4J', 'SRUN-3V7L', 'SRUN-5C9X', 'SRUN-1D6Y', 'SRUN-0F2Z',
            'SRUN-K8M3', 'SRUN-P4N7', 'SRUN-Q9R2', 'SRUN-W5T6', 'SRUN-X1B8'
        ]
        for code in initial_codes:
            cursor.execute('INSERT INTO admin_codes (code) VALUES (?)', (code,))
    
    conn.commit()
    conn.close()
    print('✅ База данных инициализирована')


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================
def get_db():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Чтобы результаты были как словари
    return conn


# ============================================
# ГЛАВНАЯ СТРАНИЦА (для проверки)
# ============================================
@app.route('/')
def index():
    """Красивая главная страница бэкенда"""
    return '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Srunington API</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #6B1D2E 0%, #4A1420 100%);
                color: #D4AF37;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                text-align: center;
                max-width: 800px;
                background: rgba(255, 255, 255, 0.05);
                padding: 50px;
                border-radius: 20px;
                border: 2px solid #D4AF37;
                box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
            }
            h1 {
                font-size: 3rem;
                letter-spacing: 4px;
                margin-bottom: 20px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
            }
            .status {
                font-size: 1.2rem;
                color: #27ae60;
                margin-bottom: 30px;
            }
            .status::before {
                content: '✅ ';
            }
            hr {
                margin: 30px auto;
                width: 200px;
                border: none;
                border-top: 2px solid #D4AF37;
            }
            h3 {
                font-size: 1.5rem;
                margin-bottom: 20px;
                letter-spacing: 2px;
            }
            ul {
                list-style: none;
                padding: 0;
                margin-top: 20px;
            }
            li {
                margin: 15px 0;
                font-size: 1.1rem;
            }
            a {
                color: #F4D03F;
                text-decoration: none;
                padding: 8px 15px;
                border: 1px solid #D4AF37;
                border-radius: 20px;
                transition: all 0.3s ease;
                display: inline-block;
            }
            a:hover {
                background: #D4AF37;
                color: #6B1D2E;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4);
            }
            .footer {
                margin-top: 40px;
                font-size: 0.9rem;
                opacity: 0.7;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏸 SRUNINGTON API</h1>
            <p class="status">Бэкенд работает!</p>
            <hr>
            <h3>Доступные эндпоинты:</h3>
            <ul>
                <li><a href="/api/health">/api/health</a> — проверка сервера</li>
                <li><a href="/api/messages">/api/messages</a> — сообщения чата</li>
                <li><a href="/api/players">/api/players</a> — игроки</li>
                <li><a href="/api/match-settings">/api/match-settings</a> — настройки матча</li>
                <li><a href="/api/mvp/current">/api/mvp/current</a> — текущий MVP</li>
                <li><a href="/api/admin/remaining-codes">/api/admin/remaining-codes</a> — коды админа</li>
            </ul>
            <div class="footer">
                <p>© 2026 Srunington Badminton Club</p>
            </div>
        </div>
    </body>
    </html>
    '''


# ============================================
# API: СООБЩЕНИЯ ЧАТА
# ============================================
@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Получить все сообщения чата"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages ORDER BY created_at ASC')
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(messages)


@app.route('/api/messages', methods=['POST'])
def post_message():
    """Отправить новое сообщение"""
    data = request.json
    
    # Валидация
    if not data.get('text') or not data.get('author'):
        return jsonify({'error': 'Текст и автор обязательны'}), 400
    
    if len(data['text']) > 500:
        return jsonify({'error': 'Слишком длинное сообщение'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO messages 
        (id, author, author_avatar, text, time, is_admin, is_edited, 
         reply_to_id, reply_to_author, reply_to_text, reply_to_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('id'),
        data['author'],
        data.get('author_avatar', '👤'),
        data['text'],
        data.get('time', datetime.now().strftime('%d.%m.%Y %H:%M')),
        1 if data.get('is_admin') else 0,
        0,
        data.get('reply_to', {}).get('id') if data.get('reply_to') else None,
        data.get('reply_to', {}).get('author') if data.get('reply_to') else None,
        data.get('reply_to', {}).get('text') if data.get('reply_to') else None,
        0
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok', 'id': data.get('id')}), 201


@app.route('/api/messages/<message_id>', methods=['PUT'])
def update_message(message_id):
    """Редактировать сообщение"""
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем, что сообщение существует и принадлежит автору
    cursor.execute('SELECT author FROM messages WHERE id = ?', (message_id,))
    msg = cursor.fetchone()
    
    if not msg:
        conn.close()
        return jsonify({'error': 'Сообщение не найдено'}), 404
    
    cursor.execute(
        'UPDATE messages SET text = ?, is_edited = 1 WHERE id = ?',
        (data['text'], message_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})


@app.route('/api/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Удалить сообщение"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Удаляем сообщение
    cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    
    # Помечаем ответы на это сообщение как удалённые
    cursor.execute('''
        UPDATE messages 
        SET reply_to_deleted = 1, reply_to_text = 'Сообщение удалено', reply_to_author = 'Неизвестный'
        WHERE reply_to_id = ?
    ''', (message_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})


# ============================================
# API: ИГРОКИ
# ============================================
@app.route('/api/players', methods=['GET'])
def get_players():
    """Получить список зарегистрированных игроков"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players ORDER BY registered_at ASC')
    players = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(players)


@app.route('/api/players', methods=['POST'])
def register_player():
    """Зарегистрировать игрока"""
    data = request.json
    
    if not data.get('device_id') or not data.get('name'):
        return jsonify({'error': 'device_id и name обязательны'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Обновляем или создаём игрока
    cursor.execute('''
        INSERT INTO players (device_id, name, avatar)
        VALUES (?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            name = excluded.name,
            avatar = excluded.avatar
    ''', (data['device_id'], data['name'], data.get('avatar', '👤')))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})


# ============================================
# API: MVP ГОЛОСОВАНИЕ
# ============================================
@app.route('/api/mvp/votes/<match_date>', methods=['GET'])
def get_mvp_votes(match_date):
    """Получить голоса за MVP на конкретный матч"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT * FROM mvp_votes WHERE match_date = ? ORDER BY created_at ASC',
        (match_date,)
    )
    votes = [dict(row) for row in cursor.fetchall()]
    
    # Группируем по игрокам
    votes_by_player = {}
    for vote in votes:
        player = vote['voted_for']
        if player not in votes_by_player:
            votes_by_player[player] = []
        votes_by_player[player].append(vote)
    
    conn.close()
    
    return jsonify({
        'total_votes': len(votes),
        'votes_by_player': {
            player: {
                'count': len(vlist),
                'voters': [{'name': v['voter_name'], 'device_id': v['voter_device_id']} for v in vlist]
            }
            for player, vlist in votes_by_player.items()
        }
    })


@app.route('/api/mvp/vote', methods=['POST'])
def vote_mvp():
    """Проголосовать за MVP"""
    data = request.json
    
    required = ['match_date', 'voter_device_id', 'voter_name', 'voted_for']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Не все обязательные поля'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO mvp_votes (match_date, voter_device_id, voter_name, voted_for)
            VALUES (?, ?, ?, ?)
        ''', (data['match_date'], data['voter_device_id'], data['voter_name'], data['voted_for']))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Вы уже проголосовали'}), 409
    
    # Обновляем текущего MVP
    cursor.execute(
        'SELECT voted_for, COUNT(*) as cnt FROM mvp_votes WHERE match_date = ? GROUP BY voted_for ORDER BY cnt DESC LIMIT 1',
        (data['match_date'],)
    )
    winner = cursor.fetchone()
    
    if winner:
        # Проверяем серию
        cursor.execute('SELECT player_name, streak FROM mvp_current WHERE id = 1')
        current = cursor.fetchone()
        
        if current and current['player_name'] == winner['voted_for']:
            new_streak = current['streak'] + 1
        else:
            new_streak = 1
        
        cursor.execute('''
            INSERT INTO mvp_current (id, player_name, streak, match_date, votes, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                player_name = excluded.player_name,
                streak = excluded.streak,
                match_date = excluded.match_date,
                votes = excluded.votes,
                updated_at = CURRENT_TIMESTAMP
        ''', (winner['voted_for'], new_streak, data['match_date'], winner['cnt']))
        conn.commit()
    
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/mvp/current', methods=['GET'])
def get_current_mvp():
    """Получить текущего MVP"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM mvp_current WHERE id = 1')
    mvp = cursor.fetchone()
    conn.close()
    
    if mvp:
        return jsonify(dict(mvp))
    return jsonify(None)


# ============================================
# API: НАСТРОЙКИ МАТЧА
# ============================================
@app.route('/api/match-settings', methods=['GET'])
def get_match_settings():
    """Получить дату и время матча"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM match_settings WHERE id = 1')
    settings = cursor.fetchone()
    conn.close()
    
    if settings:
        return jsonify(dict(settings))
    return jsonify({'match_date': '2026-06-15', 'match_time': '19:30'})


@app.route('/api/match-settings', methods=['PUT'])
def update_match_settings():
    """Обновить дату и время матча (только для админов)"""
    data = request.json
    
    # Проверяем, что пользователь — админ
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id обязателен'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE device_id = ?', (device_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Только администраторы могут менять дату'}), 403
    
    cursor.execute('''
        UPDATE match_settings 
        SET match_date = ?, match_time = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (data['match_date'], data['match_time']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})


# ============================================
# API: АДМИН-КОДЫ
# ============================================
@app.route('/api/admin/check-code', methods=['POST'])
def check_admin_code():
    """Проверить код админа"""
    data = request.json
    code = data.get('code', '').upper()
    device_id = data.get('device_id')
    
    if not code or not device_id:
        return jsonify({'error': 'Код и device_id обязательны'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем, есть ли такой код
    cursor.execute('SELECT * FROM admin_codes WHERE code = ?', (code,))
    code_row = cursor.fetchone()
    
    if not code_row:
        conn.close()
        return jsonify({'error': 'Неверный код', 'type': 'invalid'}), 404
    
    if code_row['is_used']:
        conn.close()
        return jsonify({'error': 'Код уже использован', 'type': 'used'}), 409
    
    # Активируем код
    cursor.execute('''
        UPDATE admin_codes 
        SET is_used = 1, used_by_device = ?, used_at = CURRENT_TIMESTAMP
        WHERE code = ?
    ''', (device_id, code))
    
    # Добавляем пользователя в админы
    cursor.execute('''
        INSERT INTO admins (device_id) VALUES (?)
        ON CONFLICT(device_id) DO NOTHING
    ''', (device_id,))
    
    conn.commit()
    
    # Считаем оставшиеся коды
    cursor.execute('SELECT COUNT(*) as cnt FROM admin_codes WHERE is_used = 0')
    remaining = cursor.fetchone()['cnt']
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'remaining_codes': remaining
    })


@app.route('/api/admin/check-status', methods=['POST'])
def check_admin_status():
    """Проверить, является ли устройство админом"""
    data = request.json
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'is_admin': False})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE device_id = ?', (device_id,))
    is_admin = cursor.fetchone() is not None
    conn.close()
    
    return jsonify({'is_admin': is_admin})


@app.route('/api/admin/remaining-codes', methods=['GET'])
def get_remaining_codes():
    """Получить количество оставшихся кодов (для админа)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as cnt FROM admin_codes WHERE is_used = 0')
    remaining = cursor.fetchone()['cnt']
    cursor.execute('SELECT COUNT(*) as cnt FROM admin_codes')
    total = cursor.fetchone()['cnt']
    conn.close()
    
    return jsonify({'remaining': remaining, 'total': total})


# ============================================
# ЗДОРОВЬЕ СЕРВЕРА
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


# ============================================
# ЗАПУСК СЕРВЕРА
# ============================================
if __name__ == '__main__':
    init_db()
    # Для локальной разработки
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)