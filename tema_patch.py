#!/usr/bin/env python3
"""TEMA Bruce RU XL patch for BruceDevices/firmware, LilyGO T-Embed CC1101.
Creates C++ UI renderer and bitmap glyph header during GitHub Actions build.
No font files are distributed. DejaVu font is installed on the runner.
"""
from pathlib import Path
import re
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path.cwd()
SOURCE = ROOT / 'src/core/display.cpp'
BOARD = ROOT / 'boards/lilygo-t-embed-cc1101/lilygo-t-embed-cc1101.ini'
UI = ROOT / 'src/core/tema_ui.h'

# The English strings remain in the underlying Option objects, so program logic is unchanged.
TRANSLATIONS = {
    'WiFi':'Wi-Fi', 'Wi-Fi':'Wi-Fi', 'Bluetooth':'Блютуз', 'BLE':'Блютуз',
    'RF':'Радио', 'NRF24':'NRF24', 'LoRa':'LoRa', 'FM':'FM-радио',
    'IR':'ИК-пульт', 'GPS':'GPS', 'RFID':'RFID', 'NFC':'NFC',
    'Files':'Файлы', 'File':'Файлы', 'Scripts':'Скрипты',
    'Clock':'Часы', 'Others':'Другое', 'Config':'Настройки',
    'Settings':'Настройки', 'Main Menu':'Главное меню',
    'WiFi AP':'Точка Wi-Fi', 'WiFi Scan':'Поиск Wi-Fi',
    'Scan WiFi':'Поиск Wi-Fi', 'Scan AP':'Поиск сетей',
    'Scan':'Сканировать', 'Scan/Copy':'Сканировать/копия',
    'Spectrum':'Спектр', 'Custom SubGhz':'Сигналы Sub-GHz',
    'Replay':'Повтор сигнала', 'RF Config':'Настройки радио',
    'RF Module':'Радиомодуль', 'RF Frequency':'Частота радио',
    'Connect':'Подключение', 'Connect WiFi':'Подключить Wi-Fi',
    'Disconnect':'Отключить', 'Back':'Назад', 'Exit':'Выход',
    'Cancel':'Отмена', 'Yes':'Да', 'No':'Нет', 'OK':'ОК',
    'Save':'Сохранить', 'Load':'Загрузить', 'Delete':'Удалить',
    'Open':'Открыть', 'Start':'Старт', 'Stop':'Стоп',
    'Continue':'Продолжить', 'Return':'Вернуться',
    'Brightness':'Яркость', 'Dim Time':'Время затемнения',
    'Orientation':'Поворот экрана', 'UI Color':'Цвет меню',
    'Boot Sound':'Звук запуска', 'Restart':'Перезагрузка',
    'Sleep':'Сон', 'Power Off':'Выключить', 'Information':'Информация',
    'Info':'Информация', 'About':'О программе', 'Version':'Версия',
    'SD Card':'Карта памяти', 'LittleFS':'Память устройства',
    'SD Card Mngr':'Файлы SD', 'LittleFS Mngr':'Внутр. память',
    'WebUI':'Управление с телефона', 'File Manager':'Менеджер файлов',
    'IR Receiver':'Приём ИК', 'IR Remote':'ИК-пульт',
    'Custom IR':'ИК-команды', 'TV-B-Gone':'Выключить ТВ',
    'Read tag':'Читать метку', 'Read 125kHz':'Читать 125 кГц',
    'Clone tag':'Копировать метку', 'Emulate tag':'Эмуляция метки',
    'Save file':'Сохранить файл', 'Load file':'Открыть файл',
    'Write data':'Запись данных', 'Erase data':'Очистить данные',
    'BLE Scan':'Поиск Bluetooth', 'WiFi Atks':'Атаки Wi-Fi',
    'WiFi Attacks':'Атаки Wi-Fi', 'Wardriving':'Карта сетей',
    'Scan Hosts':'Поиск устройств', 'SSH':'SSH', 'TelNet':'Telnet',
    'Time':'Время', 'Set Time':'Установить время',
    'Manual':'Вручную', 'Auto':'Автоматически',
    'Enable':'Включить', 'Disable':'Отключить',
    'Enabled':'Включено', 'Disabled':'Выключено',
    'On':'Вкл', 'Off':'Выкл', 'Low':'Низкий', 'High':'Высокий',
    'Default':'По умолчанию', 'Select':'Выбрать',
    'Language':'Язык', 'Theme':'Тема', 'Display':'Экран',
    'Hide Apps':'Скрыть программы', 'Show All':'Показать все',
    'Keyboard':'Клавиатура', 'USB Keyboard':'USB-клавиатура',
    'Send File':'Отправить файл', 'Receive File':'Принять файл',
    'Send Commands':'Отправить команды',
    'Receive Commands':'Принять команды',
    'Available':'Доступно', 'Not found':'Не найдено',
}

# 12x16 pixel cell, 2x output scaling = 24x32 (twice regular 12x16 Bruce menu text).
CELL_W, CELL_H, SCALE = 12, 16, 2
CHARS = ''.join(chr(c) for c in range(32, 127)) + ''.join(chr(c) for c in range(0x410, 0x450)) + 'Ёё'


def load_extra_dictionary():
    """Include expanded Russian on-screen label translations, without changing program logic."""
    glossary = ROOT / 'ru_extra.tsv'
    if not glossary.exists():
        raise SystemExit('Missing ru_extra.tsv next to tema_patch.py')
    for num, line in enumerate(glossary.read_text(encoding='utf-8').splitlines(), 1):
        if not line or line.lstrip().startswith('#'):
            continue
        if '\t' not in line:
            raise SystemExit(f'Invalid translation in ru_extra.tsv line {num}: expected TAB')
        en, ru = line.split('\t', 1)
        en, ru = en.strip(), ru.strip()
        if not en or not ru:
            raise SystemExit(f'Empty translation in line {num}')
        TRANSLATIONS[en] = ru


def emit_font():
    path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    if not Path(path).is_file():
        raise SystemExit('DejaVuSans font missing on build runner; apt install fonts-dejavu-core')
    font = ImageFont.truetype(path, size=15)
    font_rows = []
    for char in CHARS:
        canvas = Image.new('1', (CELL_W, CELL_H), 0)
        painter = ImageDraw.Draw(canvas)
        if char != ' ':
            # Fit each glyph into the bitmap cell (wide Cyrillic letters like Ж are not cropped).
            bbox = painter.textbbox((0, 0), char, font=font)
            w, h = max(1, bbox[2]-bbox[0]), max(1, bbox[3]-bbox[1])
            glyph = Image.new('1', (w, h), 0)
            ImageDraw.Draw(glyph).text((-bbox[0], -bbox[1]), char, font=font, fill=1)
            if w > CELL_W or h > CELL_H:
                ratio = min(CELL_W / w, CELL_H / h)
                glyph = glyph.resize((max(1, int(w*ratio)), max(1, int(h*ratio))),
                                     Image.Resampling.NEAREST)
            x = (CELL_W - glyph.width) // 2
            y = (CELL_H - glyph.height) // 2
            canvas.paste(glyph, (x,y))
        rows = []
        for yy in range(CELL_H):
            mask = 0
            for xx in range(CELL_W):
                if canvas.getpixel((xx, yy)):
                    mask |= 1 << (CELL_W - 1 - xx)
            rows.append(f'0x{mask:03x}')
        font_rows.append('{'+','.join(rows)+'}')
    cps = ','.join(str(ord(ch)) for ch in CHARS)
    data = ',\n'.join(font_rows)
    return f'''// Generated at build time. Bitmap raster data, not a font file.
#pragma once
#include <Arduino.h>
#include <vector>
static const uint16_t tema_cps[] PROGMEM = {{{cps}}};
static const uint16_t tema_bitmap[][16] PROGMEM = {{
{data}
}};
static constexpr int TEMA_CHAR_COUNT = {len(CHARS)};
static constexpr int TEMA_CW = {CELL_W};
static constexpr int TEMA_CH = {CELL_H};
'''


def cpp_literal(s):
    return s.replace('\\','\\\\').replace('"', '\\"')


def emit_ui():
    translations = ',\n'.join('    {"'+cpp_literal(k)+'", "'+cpp_literal(v)+'"}' for k,v in TRANSLATIONS.items())
    # This header is included only from display.cpp, after display.h and the globals.
    return '''// TEMA RU XL, application-layer UI only; RF and other device logic untouched.
#pragma once
#include "tema_bitmap.h"

struct TemaTranslation { const char *en; const char *ru; };
static const TemaTranslation tema_translations[] = {
''' + translations + '''
};

static int temaMin(int a, int b) { return a < b ? a : b; }
static int temaMax(int a, int b) { return a > b ? a : b; }

static String temaTranslate(const String &s) {
    for (const auto &p : tema_translations) {
        if (s == p.en) return String(p.ru);
    }
    // Safe translation of label prefixes containing changing values: "SSID: MyWifi".
    for (const auto &p : tema_translations) {
        String prefix(p.en);
        if (prefix.endsWith(":") && s.startsWith(prefix) && s.length() > prefix.length())
            return String(p.ru) + s.substring(prefix.length());
    }
    return s; // Unknown labels stay English. Logic always keeps original option labels.
}

static std::vector<uint16_t> temaChars(const String &s) {
    std::vector<uint16_t> result;
    const auto *data = reinterpret_cast<const uint8_t *>(s.c_str());
    const size_t size = s.length();
    for (size_t i = 0; i < size;) {
        uint16_t cp = '?';
        const uint8_t b = data[i++];
        if (b < 0x80) cp = b;
        else if ((b & 0xE0) == 0xC0 && i < size) {
            cp = (uint16_t(b & 0x1F) << 6) | (data[i++] & 0x3F);
        } else if ((b & 0xF0) == 0xE0 && i + 1 < size) {
            cp = (uint16_t(b & 0x0F) << 12) |
                 (uint16_t(data[i] & 0x3F) << 6) | (data[i+1] & 0x3F);
            i += 2;
        } else { while (i < size && (data[i] & 0xC0) == 0x80) i++; }
        result.push_back(cp);
    }
    return result;
}

static void temaGlyph(uint16_t cp, int x, int y, uint16_t color, int scale) {
    int idx = 0; // space fallback
    for (int i = 0; i < TEMA_CHAR_COUNT; ++i) {
        if (tema_cps[i] == cp) { idx = i; break; }
    }
    // Draw contiguous runs, not one rectangle per bitmap pixel.
    for (int row = 0; row < TEMA_CH; ++row) {
        uint16_t bits = tema_bitmap[idx][row];
        int col = 0;
        while (col < TEMA_CW) {
            while (col < TEMA_CW && !(bits & (1u << (TEMA_CW - 1 - col)))) ++col;
            int start = col;
            while (col < TEMA_CW && (bits & (1u << (TEMA_CW - 1 - col)))) ++col;
            if (col > start) tft.fillRect(x + start*scale, y + row*scale,
                                          (col - start)*scale, scale, color);
        }
    }
}

static void temaText(const String &s, int x, int y, int scale, uint16_t color,
                     int maxPx, size_t charOffset = 0, bool center = false) {
    auto cps = temaChars(s);
    int charPx = TEMA_CW * scale;
    int maxChars = maxPx / charPx;
    if (maxChars < 1) return;
    if (charOffset >= cps.size()) charOffset = 0;
    int count = temaMin((int)(cps.size() - charOffset), maxChars);
    if (center) x += (maxPx - count*charPx) / 2;
    for (int i = 0; i < count; ++i)
        temaGlyph(cps[charOffset + i], x + i*charPx, y, color, scale);
}

static bool temaBanner(const String &message, uint16_t fg, uint16_t bg) {
    String localized = temaTranslate(message);
    if (localized == message) return false;
    const int maxChars = temaMax(1, (int)(tftWidth - 28) / TEMA_CW);
    tft.fillRoundRect(5, 39, tftWidth - 10, 47, 4, bg);
    tft.drawRoundRect(5, 39, tftWidth - 10, 47, 4, fg);
    temaText(localized, 14, 43, 1, fg, tftWidth - 28);
    if ((int)temaChars(localized).size() > maxChars)
        temaText(localized, 14, 63, 1, fg, tftWidth - 28, maxChars);
    return true;
}

static Opt_Coord temaDrawFiles(int index, const std::vector<FileList> &files) {
    Opt_Coord result;
    if (files.empty()) return result;
    int n = (int)files.size();
    index = temaMax(0, temaMin(index, n - 1));
    tft.fillScreen(bruceConfig.bgColor);
    drawStatusBar();
    temaText(String("Файлы"), 8, 31, 1, bruceConfig.priColor, tftWidth - 16, 0, true);
    for (int step = -1; step <= 1; ++step) {
        int i = (index + step + n) % n;
        int y = 56 + (step + 1) * 36;
        uint16_t color = step == 0 ? bruceConfig.bgColor : bruceConfig.secColor;
        if (step == 0) tft.fillRoundRect(3, y - 1, tftWidth - 9, 35, 4, bruceConfig.priColor);
        String label = files[i].filename;
        if (files[i].folder) label = String("/") + label;
        temaText(label, 8, y, 2, color, tftWidth - 18);
    }
    result.size = 0;  // ASCII marquee is guarded in displayScrollingText.
    return result;
}

static Opt_Coord temaDrawXL(int index, std::vector<Option> &opts,
                            const String &heading, bool submenu) {
    Opt_Coord result;
    if (opts.empty()) return result;
    int n = (int)opts.size();
    index = temaMax(0, temaMin(index, n - 1));
    static String lastLabel = "";
    static size_t scroll = 0;
    if (lastLabel != opts[index].label) {
        lastLabel = opts[index].label;
        scroll = 0;
    }
    const int availableChars = (tftWidth - 29) / (TEMA_CW * 2);
    const auto selectedChars = temaChars(temaTranslate(opts[index].label));
    static unsigned long lastScrollChange = 0;
    if ((int)selectedChars.size() > availableChars && millis() - lastScrollChange > 850) {
        const size_t lastOffset = selectedChars.size() - availableChars;
        scroll = (scroll >= lastOffset) ? 0 : scroll + 1;
        lastScrollChange = millis();
    }
    tft.fillScreen(bruceConfig.bgColor);
    drawStatusBar();
    tft.drawFastHLine(3, 27, tftWidth - 6, bruceConfig.priColor);

    String title = temaTranslate(heading.length() ? heading : String("Меню"));
    temaText(title, 8, 31, 1, bruceConfig.priColor, tftWidth - 16, 0, true);

    // Three 32-pixel-tall rows, ideal for the physical 320x170 T-Embed display.
    const int top = 56;
    const int rowHeight = 36;
    for (int step = -1; step <= 1; ++step) {
        int i = (index + step + n) % n;
        int y = top + (step + 1)*rowHeight;
        uint16_t color = step == 0 ? bruceConfig.bgColor : bruceConfig.secColor;
        if (!opts[i].enabled) color = TFT_DARKGREY;
        if (step == 0) {
            tft.fillRoundRect(3, y - 1, tftWidth - 9, 35, 4, bruceConfig.priColor);
            tft.fillTriangle(7, y + 9, 7, y + 23, 16, y + 16, color);
        }
        String label = temaTranslate(opts[i].label);
        temaText(label, 20, y, 2, color, tftWidth - 29,
                 step == 0 ? scroll : 0, false);
    }
    int thumb = temaMax(5, tftHeight / n);
    tft.fillRect(tftWidth - 4, 28 + (index*(tftHeight - 28 - thumb)) / temaMax(1,n-1), 3,
                 thumb, bruceConfig.priColor);
    return result;
}

'''


def replace_once(body, old, new, label):
    count = body.count(old)
    if count != 1:
        raise SystemExit(f'Patch aborted: expected exactly one {label}, found {count}. Upstream changed.')
    return body.replace(old, new, 1)



def fix_fastled_fp_collision():
    import re
    from pathlib import Path

    root = Path.cwd()
    folders = [
        root / "src",
        root / "include",
        root / "boards",
        root / "lib" / "HAL",
    ]

    count = 0
    for folder in folders:
        if not folder.exists():
            continue
        for f in folder.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".h", ".hpp", ".cpp", ".c", ".ino"):
                continue
            old = f.read_text(
                encoding="utf-8",
                errors="surrogateescape"
            )
            new = re.sub(
                r"\bFP\b",
                "BRUCE_FONT_SMALL",
                old
            )
            if new != old:
                f.write_text(
                    new,
                    encoding="utf-8",
                    errors="surrogateescape"
                )
                count += 1

    pins = root / "boards/lilygo-t-embed-cc1101/pins_arduino.h"
    if "#define BRUCE_FONT_SMALL 1" not in pins.read_text():
        raise RuntimeError("Font macro patch failed")

    print("FastLED FP fix applied:", count)


def patch():
    load_extra_dictionary()
    fix_fastled_fp_collision()
    if not SOURCE.is_file() or not BOARD.is_file():
        raise SystemExit('Run this script inside the BruceDevices/firmware source checkout')
    src = SOURCE.read_text()
    if '#include "tema_ui.h"' in src:
        raise SystemExit('The patch was already applied')
    src = replace_once(src, '#include "display.h"',
                       '#include "display.h"\n#ifdef TEMA_RU_XL\n#include "tema_ui.h"\n#endif', 'include')
    # Guard the old ASCII marquee, which otherwise could paint over our 2x bitmap text.
    src = replace_once(src,
        'void displayScrollingText(const String &text, Opt_Coord &coord, bool highlight) {',
        '''void displayScrollingText(const String &text, Opt_Coord &coord, bool highlight) {
#ifdef TEMA_RU_XL
    if (coord.size == 0) return;
#endif''' , 'marquee guard')

    # Generic warnings/info/confirmation prompts translated when glossary contains them.
    src = replace_once(src,
        'void displayRedStripe(const String &text, uint16_t fgcolor, uint16_t bgcolor) {',
        '''void displayRedStripe(const String &text, uint16_t fgcolor, uint16_t bgcolor) {
#ifdef TEMA_RU_XL
    if (temaBanner(text, fgcolor, bgcolor)) return;
#endif''', 'notification localization')
    src = replace_once(src,
        'void printTitle(const String &title) {',
        '''void printTitle(const String &title) {
#ifdef TEMA_RU_XL
    if (temaTranslate(title) != title) {
        tft.fillRect(8, BORDER_PAD_Y, tftWidth - 16, 18, bruceConfig.bgColor);
        temaText(temaTranslate(title), 8, BORDER_PAD_Y, 1,
                 bruceConfig.priColor, tftWidth - 16, 0, true);
        return;
    }
#endif''', 'header localization')
    # Include is after display.h, but before other includes. This is safe since display.h pulls in globals.
    src = replace_once(src, '    bool renderedByLambda = false;\n            if (options[index].hover)',
                       '''    bool renderedByLambda = false;
#ifdef TEMA_RU_XL
            if (menuType == MENU_TYPE_MAIN) {
                temaDrawXL(index, options, String("Главное меню"), true);
                renderedByLambda = true;
            }
#endif
            if (!renderedByLambda && options[index].hover)''', 'main menu renderer')
    src = replace_once(src,
        '''        if (menuType == MENU_TYPE_REGULAR) {
            String txt = options[index].label;
            displayScrollingText(txt, coord, true);
        }''',
        '''        if (menuType == MENU_TYPE_REGULAR) {
#ifndef TEMA_RU_XL
            String txt = options[index].label;
            displayScrollingText(txt, coord, true);
#endif
        }
#ifdef TEMA_RU_XL
        static unsigned long temaScrollTick = 0;
        if (millis() - temaScrollTick > 850) {
            temaScrollTick = millis();
            // Refresh pages to keep long labels visible; navigation remains native Bruce.
            if (menuType == MENU_TYPE_MAIN)
                temaDrawXL(index, options, String("Главное меню"), false);
            else if (menuType == MENU_TYPE_SUBMENU)
                temaDrawXL(index, options, String(subText), true);
            else if (menuType == MENU_TYPE_REGULAR)
                temaDrawXL(index, options, String("Меню"), false);
        }
#endif''', 'disable English marquee')
    pattern = re.compile(r'(Opt_Coord drawOptions\(\s*int index, std::vector<Option> &options, uint16_t fgcolor, uint16_t selcolor, uint16_t bgcolor,\s*bool firstRender\s*\) \{)')
    src,count = pattern.subn(r'\1\n#ifdef TEMA_RU_XL\n    return temaDrawXL(index, options, String("Меню"), false);\n#endif',src)
    if count != 1: raise SystemExit(f'Cannot patch drawOptions: {count} matches')
    src = replace_once(src, 'Opt_Coord listFiles(int index, std::vector<FileList> fileList) {',
        '''Opt_Coord listFiles(int index, std::vector<FileList> fileList) {
#ifdef TEMA_RU_XL
    return temaDrawFiles(index, fileList);
#endif''', 'file manager')
    src = replace_once(src, 'void drawSubmenu(int index, std::vector<Option> &options, const char *title) {',
        '''void drawSubmenu(int index, std::vector<Option> &options, const char *title) {
#ifdef TEMA_RU_XL
    temaDrawXL(index, options, String(title), true);
    return;
#endif''', 'submenu renderer')
    SOURCE.write_text(src)
    ini = BOARD.read_text()
    if '-DTEMA_RU_XL' not in ini:
        ini = replace_once(ini, '-DDEVICE_NAME=\'"Lilygo T-Embed CC1101"\'',
                           '-DDEVICE_NAME=\'"Lilygo T-Embed CC1101"\'\n\t-DTEMA_RU_XL',
                           'board build flag')
        BOARD.write_text(ini)
    (ROOT/'src/core/tema_bitmap.h').write_text(emit_font())
    UI.write_text(emit_ui())
    print('TEMA RU XL applied to', SOURCE)
    print('Translated UI labels:', len(TRANSLATIONS))


if __name__=='__main__':
    patch()
