# 🍋 LimeLang

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![LuaJIT](https://img.shields.io/badge/Engine-LuaJIT-2C2D72.svg)](https://luajit.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)](https://github.com/Ilya5627/LimeLang-Transpiler)

**Python-подобная выразительность. Производительность LuaJIT. Гибкость системного уровня.**

**Lime** — это современный транслируемый язык программирования, созданный для тех, кто устал выбирать между простотой кода и скоростью его выполнения. Он предлагает чистый, лаконичный синтаксис в духе Python, но под капотом генерирует высокооптимизированный код для молниеносного движка **LuaJIT**, с нативной поддержкой C-библиотек (FFI) и реактивным программированием из коробки.

> 🚀 *Пишите как на Python. Работайте как на C. Исполняйте на скорости LuaJIT.*

---

## 🤔 Почему именно Lime?


| Язык    | Проблема, которую решает Lime                                                                                                                                     |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Python**  | Слишком медленный для real-time задач и игр.                                                                                                               |
| **C / C++** | Сложный синтаксис, ручное управление памятью, долгая компиляция.                                                                |
| **Lua**     | 1-индексация массивов, отсутствие современного синтаксиса, слабая стандартная библиотека.                 |
| **🍋 Lime** | **Решает всё вышеперечисленное:** 0-индексация, современный синтаксис, скорость JIT и прямой доступ к C. |

### Ключевые преимущества:

1. **Один файл — один проект.** Никаких `CMake`, `requirements.txt` или сложных сборщиков. Просто напишите код и запустите его.
2. **Встроенная реактивность.** Система сигналов (`ref`, `live`, `watch`) прямо в ядре, вдохновленная SolidJS/Vue, идеальна для UI и игровых состояний.
3. **Бесшовный FFI.** Подключайте `.dll` / `.so` и описывайте C-структуры прямо в коде Lime.
4. **Эргономичные ошибки.** Компилятор мапит ошибки Lua обратно на строки вашего исходного `.lm` файла с красивой подсветкой.

---

## ⚙️ Как это работает? (Микро-архитектура)

Lime не является интерпретатором в классическом понимании. Это **транспилятор**, который работает по следующему конвейеру за доли миллисекунд:

```text
[ main.lm ] 
    │
    ├─▶ 1. Lexer & Parser  → Построение Абстрактного Синтаксического Дерева (AST)
    ├─▶ 2. Code Generator  → Преобразование AST в оптимизированный Lua-код
    ├─▶ 3. Prelude Inject  → Внедрение стандартной библиотеки (0-индексация, реактивность, FFI)
    │
[ output.lua ] ──▶ 4. LuaJIT Runtime → Мгновенная JIT-компиляция и выполнение
```

---

## Примеры кода на Lime

### 1. Fizz-Buzz

```rust
for i = 1, 100, 1 {
    match [i % 3 == 0, i % 5 == 0]:
        case [true, true] {
            print("FizzBuzz")
        }
        case [false, true] {
            print("Buzz")
        }
        case [true, false] {
            print("Fizz")
        }
        case _ {
            print(i)
        }
}
```

### 2. Калькулятор

```kotlin
var calculate = 0

var sqrt = (fn() = calculate * calculate) >> live

var add = fn(a, b) = a + b
var sub = fn(a, b) = a - b
var mul = fn(a, b) = a * b
var div = fn(a, b) = a / b

calculate = 123 >> add(5) >> div(156) >> add(6) >> mul(10) // Оператор пайплайн для читаемого формата

calculate >> print
```

### 3. Http запросы

```swift
use "nicehttp"
var post_data = "name=LIME&age=123&city=Somewhere"
var post_headers = {"Content-Type": "application/x-www-form-urlencoded"}
res = post("https://httpbin.org/post", post_data, post_headers)
print("Status:", res["status"])
if res["status"] == 200 {
    print("Body:", res["body"])
} else {
    print("Error:", res["error"])
}
```

### 4. Car-class

```rust
struct Car {
    speed: f
    model: s
}

c = Car(100, "Lamborghini Aventador")

Car:ride () {
    print(self.model.." is riding with speed "..self.speed)
}

c::ride()
```

## ✨ Возможности и Синтаксис

### 1. Лаконичность и чистота

Никакого синтаксического шума. Только суть.

```rust
var name = "Lime"
var version = 1.0

fn greet(user) {
    ret "Hello, " + user + "! Welcome to v" + version
}

if version >= 1.0 {
    print(greet(name))
}
```

### 2. Конвейерный оператор (`>>`)

Обрабатывайте данные элегантно, без вложенных вызовов функций ("ад колбэков"). Данные передаются как первый аргумент в следующую функцию.

```kotlin
var numbers = [1, 2, 3, 4, 5]

// Умножаем каждый элемент на 2 и суммируем результат
var result = numbers 
    >> map(fn(x) = x * 2) 
    >> sum()

print(result) // 30
```

### 3. Встроенная Реактивность (Signals)

Управляйте состоянием декларативно. Идеально для сложных систем без сторонних библиотек.

```lime
var count = ref(0)

// Вычисляемое значение: обновляется автоматически при изменении зависимостей
var double_count = live(fn() = count.value * 2)

// Слежение за изменениями
watch(fn() {
    print("Count изменился на:", count.value)
})

count.value = 10 // Автоматически вызовет watch и обновит double_count.value до 20
```

### 4. Исправленные структуры данных (0-индексация)

Lime исправляет главную "боль" Lua. Массивы начинаются с `0`, а строки и числа получают богатый набор методов из коробки.

```lime
var users = ["Alice", "Bob", "Charlie"]
print(users[0])        // "Alice"
print(users[-1])       // "Charlie" (поддержка отрицательных индексов)

users.push("Dave")
print(users.len())     // 4

var text = "  hello world  "
print(text.trim().upper().split(" ")) // ["HELLO", "WORLD"]
```

### 5. Нативная работа с C (FFI)

Используйте мощь системных библиотек без написания обвязок на C.

```lime
// Подключаем библиотеку и описываем C-структуру
usec "physics_lib" {
    rule: "typedef struct { float x; float y; } Vector2;"
}

// Создаем экземпляр структуры
var pos = Vector2(10.5, 20.0)
print(pos.x) // 10.5

// Вызов C-функции из библиотеки (пример)
// physics_lib.move_vector(pos, 5.0)
```

---

## 🛠 Быстрый старт

### Требования

* Python 3.8 или выше
* Библиотека `lupa` (Python-обертка над LuaJIT)

### Установка зависимостей

```bash
pip install lupa
```

### Запуск проекта

Lime поддерживает как запуск отдельных файлов, так и целых директорий.

```bash
# Запуск конкретного файла
python main.py path/to/script.lm

# Запуск проекта (автоматически ищет main.lm в папке)
python main.py ./my_project

# Запуск уже скомпилированного output.lua (пропускает парсинг, максимальная скорость)
python main.py ./my_project --lua

# Скрыть таймер выполнения
python main.py ./my_project --notime
```

---

## 🎨 Красивая обработка ошибок

Lime заботится о вашем времени. Компилятор перехватывает ошибки Lua и показывает их **в контексте вашего исходного кода Lime**, а не сгенерированного Lua-файла.

```text
Lime Error: variable 'health' is not defined
 --> main.lm:14
 12 | fn take_damage(amount) {
 13 |     var new_hp = health - amount
 14 |     health = new_hp
    |     ^^^^^^^^^^^^^^^^
Hint: do you want to write 'var' before health?
```

---

## 📂 Структура проекта

Типичный проект на Lime максимально прост и не требует конфигурационных файлов:

```text
my_lime_project/
├── main.lm          # Точка входа в приложение
├── utils.lm         # Дополнительные модули (подключаются через load "utils")
├── libs/            # Локальные C-библиотеки (.dll / .so / .dylib)
└── output.lua       # (Генерируется автоматически) Скомпилированный код
```

---

## 🗺 Roadmap (Планы развития)

- [X]  Базовый синтаксис и типы данных
- [X]  Оператор конвейера (`>>`)
- [X]  Реактивная система (`ref`, `live`, `watch`)
- [X]  FFI и описание C-структур (`usec`)
- [X]  Красивые трейсбеки ошибок с привязкой к исходному коду
- [ ]  Компиляция в standalone исполняемые файлы (`--build-exe`)
- [X]  Собственный пакетный менеджер и реестр модулей
- [ ]  Поддержка асинхронности (`async` / `await`)
- [ ]  Перегрузка операторов

---

## 🤝 Участие в разработке

Lime находится в стадии активной **Beta-разработки**. Мы открыты к предложениям и критике!
Нашли баг? Хотите добавить новый синтаксический сахар? Создавайте Issue или отправляйте Pull Request.

🔗 **Репозиторий:** [github.com/Ilya5627/LimeLang-Transpiler](https://github.com/Ilya5627/LimeLang-Transpiler)

---

<p align="center">
  <i>Сделано с 🍋 и любовью к чистому, быстрому коду.</i>
</p>
