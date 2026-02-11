import json
import re

STANDARD_INDENT = '    '
BASE_INDENT_SAVE_ZMOD_DATA = 1
BASE_INDENT_GET_ZMOD_DATA = 1
BASE_INDENT_RESET_ZMOD = 1
BASE_INDENT_GLOBAL = 1

DEFAULT_VALUE_ASSUMPTION = 0
DEFAULT_STRING_ASSUMPTION = ""
TYPE_ASSUMPTION = 'int'

def add_save_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_SAVE_ZMOD_DATA
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** BEGIN SAVE_ZMOD_DATA TEMPLATE SETTINGS ** #')
    file_data.append(indent_level * STANDARD_INDENT)
    
    for category, cat_data in categories.items():
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
            
            if set_data.get('require_ad5x', 0) != 0:
                if set_data.get('require_ad5x', 0) > 0:
                    file_data.append((indent_level * STANDARD_INDENT) + "{% if client.ad5x %}")
                else:
                    file_data.append((indent_level * STANDARD_INDENT) + "{% if not client.ad5x %}")
                indent_level += 1
                
            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if params.{setting.upper()} %}}")
            indent_level += 1
            
            if set_data.get('type', TYPE_ASSUMPTION) == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"{{ set z{setting} = params.{setting.upper()}|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"{{z{setting.lower()}}}\"")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{ set z{setting} = params.{setting.upper()}|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{set_data.get('type', TYPE_ASSUMPTION)} %}}")
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={{z{setting.lower()}}}")
            
            indent_level -= 1
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                                 
            if set_data.get('require_ad5x', 0) != 0:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                                
            file_data.append(indent_level * STANDARD_INDENT)
            
    file_data.append((indent_level * STANDARD_INDENT) + '# ** END SAVE_ZMOD_DATA TEMPLATE SETTINGS ** #')
    
def add_get_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_GET_ZMOD_DATA
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** BEGIN GET_ZMOD_DATA TEMPLATE SETTINGS ** #')
    file_data.append(indent_level * STANDARD_INDENT)
    
    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"info\" MSG=\"{cat_data.get("get_zmod_data_text", "")}\"")
        file_data.append(indent_level * STANDARD_INDENT)
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
                
            if set_data.get('require_ad5x', 0) != 0 or set_data.get('require_native_screen', 0) != 0:
                if set_data.get('require_ad5x', 0) != 0 and set_data.get('require_native_screen', 0) != 0:
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {"not " if set_data.get('require_ad5x', 0) < 0 else ""}client.ad5x and screen == {"true" if set_data.get('require_native_screen', 0) > 0 else "false"} %}}")
                elif set_data.get('require_ad5x', 0) != 0:
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {"not " if set_data.get('require_ad5x', 0) < 0 else ""}client.ad5x %}}")
                else: # require_native_screen != 0 is implied
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if screen == {"true" if set_data.get('require_native_screen', 0) > 0 else "false"} %}}")
                indent_level += 1
            
            condition = set_data.get('condition', None)
            if condition != None:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {condition} %}}")
                indent_level += 1
            setting_type = set_data.get('type', TYPE_ASSUMPTION)
            
            if setting_type == 'string':
                quote = '"'
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
            else:
                quote = ''
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")
                
            had_generic = False
            is_first = True
            for text_condition, text in set_data.get('get_zmod_data_text', {}).items():
                if text_condition == '*':
                    had_generic = True
                    if not is_first:
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                else:
                    had_regular = True
                    prefix = "" if is_first else "el" # "if" or "elif"
                    
                    if not is_first:
                        indent_level -= 1
                        
                    check_5x = 0
                    check_native_screen = 0
                    
                    if setting_type != 'string':
                        if 'n' in text_condition:
                            check_native_screen = 1
                        if 'x' in text_condition:
                            check_5x = 1
                        if 'm' in text_condition:
                            check_5x = -1
                        text_condition = re.sub(r'[mnx]', '', text_condition)
                    
                    condition_string = f"{prefix}if z{setting.lower()} == "
                    
                    if setting_type == 'string':
                        condition_string += f"\"{text_condition}\""
                    else:
                        condition_string += f"{text_condition}"
                        
                    if check_native_screen != 0:
                        condition_string += " and screen == True"
                    
                    if check_5x > 0:
                        condition_string += " and client.ad5x"
                    elif check_5x < 0:
                        condition_string += " and not client.ad5x"
                        
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% {condition_string} %}}")    
                    indent_level += 1
                    
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"{text} // SAVE_ZMOD_DATA {setting.upper()}={quote}{{z{setting.lower()}}}{quote}\"")
                
                if had_generic:
                    break
                
                is_first = False
                    
            if not had_generic:
                if not is_first:
                    file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"===Unrecognized value for setting:=== {setting.upper()} // SAVE_ZMOD_DATA {setting.upper()}={quote}{{z{setting.lower()}}}{quote}\"")
                
            if not is_first or not had_generic:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")                
                
            file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={quote}{{z{setting.lower()}}}{quote}")

            if condition != None:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                
            if set_data.get('require_ad5x', 0) != 0 or set_data.get('require_native_screen', 0) != 0:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            
            file_data.append(indent_level * STANDARD_INDENT)                
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** END GET_ZMOD_DATA TEMPLATE SETTINGS ** #')

def add_reset_zmod(file_data, categories, settings):
    indent_level = BASE_INDENT_RESET_ZMOD
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** BEGIN _RESET_ZMOD TEMPLATE SETTINGS ** #')
    file_data.append(indent_level * STANDARD_INDENT)        
    
    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"# {category}")
        both_entries = []
        ad5m_entries = []
        ad5x_entries = []
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
            check_ad5x = set_data.get('require_ad5x', 0)
            if check_ad5x < 0:
                target = ad5m_entries
                extra_indent = 1
            elif check_ad5x > 0:
                target = ad5x_entries
                extra_indent = 1
            else:
                target = both_entries
                extra_indent = 0
            
            if set_data.get('type', TYPE_ASSUMPTION) == 'string':
                target.append(((indent_level + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\"")
            else:
                target.append(((indent_level + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={set_data.get('default', DEFAULT_VALUE_ASSUMPTION)}")
        
        file_data += both_entries
        
        if len(ad5m_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if not client.ad5x %}")
            file_data += ad5m_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            
        if len(ad5x_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if client.ad5x %}")
            file_data += ad5x_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            
        file_data.append(indent_level * STANDARD_INDENT)        
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** END _RESET_ZMOD TEMPLATE SETTINGS ** #')
            
    
def add_global(file_data, categories, settings):
    indent_level = BASE_INDENT_GLOBAL
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** BEGIN _GLOBAL TEMPLATE SETTINGS ** #')
    file_data.append(indent_level * STANDARD_INDENT)                
    
    file_data.append((indent_level * STANDARD_INDENT) + '# ** END _GLOBAL TEMPLATE SETTINGS ** #')
    file_data.append(indent_level * STANDARD_INDENT)

def main():
    with open('zmod_settings.json', 'r', encoding='utf-8') as f:
        settings_json_data = json.load(f)
        
    categories = settings_json_data['Categories']
    settings = settings_json_data['Settings']
    
    file_data = []
    
    with open('base.cfg', 'r', encoding='utf-8') as f:
        skip_mode = False
        for line in f:
            if line.strip().startswith('# ** BEGIN'):
                skip_mode = True
                if line.strip() == '# ** BEGIN SAVE_ZMOD_DATA TEMPLATE SETTINGS ** #':
                    add_save_zmod_data(file_data, categories, settings)
                if line.strip() == '# ** BEGIN GET_ZMOD_DATA TEMPLATE SETTINGS ** #':
                    add_get_zmod_data(file_data, categories, settings)
                if line.strip() == '# ** BEGIN _RESET_ZMOD TEMPLATE SETTINGS ** #':
                    add_reset_zmod(file_data, categories, settings)
                if line.strip() == '# ** BEGIN _GLOBAL TEMPLATE SETTINGS ** #':
                    add_global(file_data, categories, settings)
            if not skip_mode:
                file_data += [line]
            if line.strip().startswith('# ** END'):
                skip_mode = False
                
    with open('base-out.cfg', 'w', encoding='utf-8') as f:
        for line in file_data:
            f.write(line)
            if not line.endswith('\n'):
                f.write('\n')

if __name__ == "__main__":
    main()