import subprocess
import threading
import time
import appium  
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from datetime import datetime

def appium_server():
    def start_appium():
        subprocess.Popen(["appium"])
    
    thread = threading.Thread(target=start_appium)
    thread.daemon = True
    return thread

def dispositivo_adb():
    dispositivo = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    nome_do_dispositivo = dispositivo.stdout.split('\n')
    for linha in nome_do_dispositivo[1:]:
        if 'device' in linha:
            dispositivo_id = linha.split()[0]
            return dispositivo_id
    return None 

def iniciar_sou_govsp():
    thread = appium_server() 
    thread.start()
    time.sleep(3)

    dispositivo_id = dispositivo_adb()
    if not dispositivo_id:
        raise Exception("Nenhum dispositivo encontrado")

    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.device_name = dispositivo_id
    options.app_package = 'br.gov.sp.prodesp.sousp'
    options.app_activity = 'br.gov.sp.prodesp.sousp/com.servicenow.mobilesky.LaunchActivity'
    options.no_reset = True

    buscador = webdriver.Remote("http://localhost:4723", options=options)
    espera_curta = WebDriverWait(buscador, 20)
    espera_media = WebDriverWait(buscador, 40)
    espera_longa = WebDriverWait(buscador, 60)  
    
    return buscador, espera_curta, espera_media, espera_longa

def login():
    cpf = input("Digite seu CPF: ")
    senha = input("Digite sua senha: ")
    return cpf, senha

def espera_mensagem_dois_fatores(buscador):
    try:
        espera_popup_dois_fatores = WebDriverWait(buscador, 10)
        espera_popup_dois_fatores.until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='skipMandatoryMfaButton']"))).click()
        return True
    except TimeoutException:
        return False

def permitir_localizacao(buscador, espera_curta):
    try:
        espera_curta.until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@content-desc='Allow this time']"))).click()
        return True
    except TimeoutException:
        return False

def aguardar_mensagem_processamento(buscador, espera_longa):
    try:
        print("Aguardando processamento...")
        espera_longa.until(
            EC.presence_of_element_located((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/snackbar_text' and @text='Aguarde... Buscando informações...']"))
        )
        
        try:
            espera_longa.until(
                EC.presence_of_element_located((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/snackbar_text' and @text='PDF gerado e disponível para download!']"))
            )
            print("✅ PDF gerado com sucesso!")
            return 'sucesso'
            
        except TimeoutException:
            try:
                espera_longa.until(
                    EC.presence_of_element_located((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/snackbar_text' and @text='Ocorreu um erro ao processar o pedido. Contate o suporte.']"))
                )
                print("❌ Erro no processamento")
                return 'erro'
            except TimeoutException:
                print("⚠️ Mensagem final não identificada")
                return 'timeout'
                
    except TimeoutException:
        print("⚠️ Mensagem de processamento não apareceu")
        return 'timeout'

def processar_mes_com_retry(buscador, espera_longa, data_mes_ano, cargo_numero, max_tentativas=3):
    for tentativa in range(max_tentativas):
        try:
            print(f"Tentativa {tentativa + 1}/{max_tentativas} para {data_mes_ano}")
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.view.View[@text='Mês de referência']"))).click()
            
            campo_mes = espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='s2id_autogen3_search']")))
            campo_mes.clear()
            campo_mes.send_keys(data_mes_ano)
            
            xpath_mes = f"//android.widget.TextView[@text='{data_mes_ano}']"
            elemento_mes = espera_longa.until(EC.element_to_be_clickable((By.XPATH, xpath_mes)))
            elemento_mes.click()
            
            print(f"Aguardando confirmação da seleção do mês {data_mes_ano}...")
            resultado_mes = aguardar_mensagem_processamento(buscador, espera_longa)
            if resultado_mes == 'erro':
                print(f"❌ Erro ao selecionar mês {data_mes_ano}")
                if tentativa < max_tentativas - 1:
                    if not voltar_pagina_inicial_e_contracheque(buscador, espera_longa):
                        return False
                    time.sleep(60)
                    continue
                return False
            elif resultado_mes == 'timeout':
                print(f"⚠️ Timeout ao aguardar confirmação do mês {data_mes_ano}")
            
            resultado = aguardar_mensagem_processamento(buscador, espera_longa)
            
            if resultado == 'erro':
                print(f"❌ Erro ao processar {data_mes_ano}")
                if tentativa < max_tentativas - 1:
                    if not voltar_pagina_inicial_e_contracheque(buscador, espera_longa):
                        return False
                    time.sleep(60)
                    continue
                return False
            elif resultado == 'timeout':
                print(f"⚠️ Timeout no processamento de {data_mes_ano}")
                if tentativa < max_tentativas - 1:
                    if not voltar_pagina_inicial_e_contracheque(buscador, espera_longa):
                        return False
                    time.sleep(60)
                    continue
                return False
            
            espera_longa.until(
                EC.presence_of_element_located((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/snackbar_text' and @text='Carregando PDF']")))
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@text='Visualizar PDF']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='android:id/button1']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@text='Baixar PDF']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='download']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@content-desc='Add to Drive']"))).click()
            
            nome_arquivo = f"{data_mes_ano}_cargo{cargo_numero}"
            campo_nome = espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='com.google.android.apps.docs:id/upload_title_edittext']")))
            campo_nome.clear()
            campo_nome.send_keys(nome_arquivo)
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='com.google.android.apps.docs:id/save_button']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageButton[@content-desc='Back']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.TextView[@content-desc='Contracheque']"))).click()
                
            return True
            
        except TimeoutException as e:
            print(f"❌ Timeout na tentativa {tentativa + 1} para {data_mes_ano}: {e}")
            if tentativa < max_tentativas - 1:
                if not voltar_pagina_inicial_e_contracheque(buscador, espera_longa):
                    return False
                time.sleep(60)
            else:
                return False
        except Exception as e:
            print(f"❌ Erro na tentativa {tentativa + 1} para {data_mes_ano}: {e}")
            if tentativa < max_tentativas - 1:
                if not voltar_pagina_inicial_e_contracheque(buscador, espera_longa):
                    return False
                time.sleep(60)
            else:
                return False
    
    return False

def tutorial_app(buscador, espera_media):
    try:
        elemento = espera_media.until(
            EC.presence_of_element_located((By.XPATH, "//android.widget.Button[@content-desc='Allow this time']"))
        )
        elemento.click()
        return True
    except TimeoutException:
        return False
    except WebDriverException as e:
        if "instrumentation process is not running" in str(e):
            print("❌ UiAutomator2 crashed. Reinicie Appium e tente novamente.")
            raise SystemExit("Reinicie Appium e execute o script novamente")
        return False

def cargos(buscador, espera_longa):
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Profile image']"))).click()
    
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/tv_title' and @text='Vínculo']"))).click()

def escolher_cargo(buscador, espera_longa):
    max_tentativas = 3
    
    for tentativa in range(max_tentativas):
        try:
            print(f"Buscando cargos (tentativa {tentativa + 1})...")
            time.sleep(2)
            
            todos_elementos = espera_longa.until(
                EC.presence_of_all_elements_located((By.XPATH, "//android.widget.TextView")))
            
            linhas_cargo = []
            
            for i, elemento in enumerate(todos_elementos):
                try:
                    content_desc = elemento.get_attribute('content-desc')
                    if content_desc and content_desc in ['Ativo', 'Inativo']:
                        texto_elementos = []
                        
                        for j in range(max(0, i-3), i+1):
                            if j < len(todos_elementos):
                                try:
                                    texto = todos_elementos[j].text
                                    if texto and texto.strip():
                                        texto_elementos.append(texto.strip())
                                except StaleElementReferenceException:
                                    break
                        
                        if texto_elementos:
                            linhas_cargo.append({
                                'texto': ' - '.join(texto_elementos),
                                'index': i
                            })
                
                except StaleElementReferenceException:
                    print("Elemento obsoleto detectado, recarregando...")
                    break
                except Exception:
                    continue
            
            if linhas_cargo:
                print("Cargos encontrados:")
                for i, linha in enumerate(linhas_cargo, 1):
                    print(f"{i}. {linha['texto']}")
                
                while True:
                    try:
                        escolha = int(input("Escolha o número do cargo desejado: ")) - 1
                        if 0 <= escolha < len(linhas_cargo):
                            
                            todos_elementos_fresh = espera_longa.until(
                                EC.presence_of_all_elements_located((By.XPATH, "//android.widget.TextView")))
                            
                            cargo_index = linhas_cargo[escolha]['index']
                            if cargo_index < len(todos_elementos_fresh):
                                cargo_escolhido = todos_elementos_fresh[cargo_index]
                                cargo_escolhido.click()
                                
                                espera_longa.until(
                                    EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='br.gov.sp.prodesp.sousp:id/parameterSubmitButton']"))).click()
                                
                                espera_longa.until(
                                    EC.element_to_be_clickable((By.XPATH, "//android.widget.FrameLayout[@content-desc='Tab Página inicial']"))).click()
                                
                                espera_longa.until(
                                    EC.element_to_be_clickable((By.XPATH, "//android.view.ViewGroup[@content-desc='icon Contracheque Button ']"))).click()
                                
                                return escolha + 1
                        else:
                            print("Número inválido.")
                    except ValueError:
                        print("Digite um número válido.")
                    except StaleElementReferenceException:
                        print("Elemento obsoleto, tente novamente.")
                        break
                        
        except StaleElementReferenceException:
            if tentativa < max_tentativas - 1:
                print("Elementos obsoletos, tentando novamente...")
                time.sleep(3)
                continue
            else:
                print("Erro persistente com elementos obsoletos")
                return None
        except Exception as e:
            if tentativa < max_tentativas - 1:
                print(f"Erro: {e}, tentando novamente...")
                time.sleep(3)
                continue
            else:
                print(f"Erro persistente: {e}")
                return None
    
    return None

def baixar_contracheques(buscador, espera_longa, cargo_numero=1, anos_para_processar=None, ano_inicial=None, mes_inicial=None):
    anos_com_erro = []
    meses_com_erro = []
    
    if anos_para_processar is None:
        anos_range_1 = list(range(2000, 2013))
        anos_range_2 = list(range(2017, datetime.now().year + 1))
        anos_para_processar = anos_range_1 + anos_range_2
    
    meses = [f"{i:02d}" for i in range(1, 14)]
    
    for ano in anos_para_processar:
        if ano_inicial is not None and ano < ano_inicial:
            continue
            
        print(f"Processando ano {ano}...")
        
        try:
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.view.View[@text='Tipo de solicitação']"))).click()
            
            search_box = espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='s2id_autogen1_search']")))
            search_box.clear()
            search_box.send_keys("Anteriores")
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.view.View[contains(@resource-id, 'select2-result') and @text='Anteriores']"))).click()
            
            resultado_anteriores = aguardar_mensagem_processamento(buscador, espera_longa)
            if resultado_anteriores == 'erro':
                anos_com_erro.append(ano)
                continue
            
            try:
                espera_longa.until(
                    EC.element_to_be_clickable((By.XPATH, "//android.view.View[@resource-id='s2id_sp_formfield_reference_year']"))).click()
            except TimeoutException:
                try:
                    espera_longa.until(
                        EC.element_to_be_clickable((By.XPATH, "//android.view.View[@text='Ano de referência']"))).click()
                except TimeoutException:
                    anos_com_erro.append(ano)
                    continue
            
            campo_ano = espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='s2id_autogen2_search']")))
            campo_ano.clear()
            campo_ano.send_keys(str(ano))
            
            xpath_ano = f"//android.widget.TextView[@text='{ano}']"
            elemento_ano = espera_longa.until(EC.element_to_be_clickable((By.XPATH, xpath_ano)))
            elemento_ano.click()
            
            resultado_ano = aguardar_mensagem_processamento(buscador, espera_longa)
            if resultado_ano == 'erro':
                anos_com_erro.append(ano)
                continue
            
            for mes in meses:
                data_mes_ano = f"{mes}/{ano}"
                print(f"Processando {data_mes_ano}...")
                
                sucesso = processar_mes_com_retry(buscador, espera_longa, data_mes_ano, cargo_numero)
                if not sucesso:
                    meses_com_erro.append(data_mes_ano)
                    
        except Exception as e:
            print(f"Erro no ano {ano}: {e}")
            anos_com_erro.append(ano)
    
    return anos_com_erro, meses_com_erro

def processar_cargo_escolhido(buscador, espera_longa, espera_media):
    cargo_escolhido = escolher_cargo(buscador, espera_longa)
    
    if cargo_escolhido:
        anos_erro, meses_erro = baixar_contracheques(buscador, espera_longa, cargo_escolhido)
        return anos_erro, meses_erro
    else:
        return [], []

def voltar_pagina_inicial_e_contracheque(buscador, espera_longa, max_tentativas=3):
    for tentativa in range(max_tentativas):
        try:
            print(f"Tentativa {tentativa + 1}/{max_tentativas}: Voltando à página inicial...")
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.widget.FrameLayout[@content-desc='Tab Página inicial']"))).click()
            
            espera_longa.until(
                EC.element_to_be_clickable((By.XPATH, "//android.view.ViewGroup[@content-desc='icon Contracheque Button ']"))).click()
            
            time.sleep(2)
            return True
            
        except TimeoutException:
            if tentativa < max_tentativas - 1:
                print(f"Falha na tentativa {tentativa + 1}. Aguardando 1 minuto...")
                time.sleep(60)
            else:
                print("Falha em todas as tentativas de voltar à página inicial")
                return False
    
    return False

def obter_lista_cargos(driver, espera_media):
    todos_elementos = espera_media.until(
        EC.presence_of_all_elements_located((By.XPATH, "//android.widget.TextView")))
    
    linhas_cargo = []
    
    for i, elemento in enumerate(todos_elementos):
        try:
            content_desc = elemento.get_attribute('content-desc')
            if content_desc in ['Ativo', 'Inativo']:
                linha_elementos = []
                
                if i >= 3:
                    for j in range(i-3, i+1):
                        if j < len(todos_elementos):
                            desc = todos_elementos[j].get_attribute('content-desc')
                            if desc:
                                linha_elementos.append(desc)
                
                if len(linha_elementos) >= 4:
                    texto_completo = ' '.join(linha_elementos)
                    linhas_cargo.append({
                        'texto': texto_completo,
                        'elemento': elemento
                    })
                else:
                    linhas_cargo.append({
                        'texto': content_desc,
                        'elemento': elemento
                    })
        except Exception:
            continue
    
    return linhas_cargo

def trocar_cargo(driver, espera_longa):
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.FrameLayout[@content-desc='Tab Página inicial']"))).click()
    
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Profile image']"))).click()
    
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.TextView[@resource-id='br.gov.sp.prodesp.sousp:id/tv_title' and @text='Vínculo']"))).click()

def perguntar_retry(anos_erro, meses_erro):
    if not anos_erro and not meses_erro:
        print("Todos os contracheques foram baixados com sucesso!")
        return False
    
    print("=== RELATÓRIO DE ERROS ===")
    
    if anos_erro:
        print("Anos não encontrados:")
        for ano, cargo in anos_erro:
            print(f"  - Ano {ano} (Cargo {cargo})")
    
    if meses_erro:
        print("Meses com erro:")
        for mes, cargo in meses_erro:
            print(f"  - {mes} (Cargo {cargo})")
    
    resposta = input("Tentar novamente os itens com erro? (s/n): ").lower().strip()
    return resposta == 's'

def entrar_no_app():
    cpf, senha = login()
    buscador, espera_curta, espera_media, espera_longa = iniciar_sou_govsp()
    
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='br.gov.sp.prodesp.sousp:id/login']"))).click()
    
    permitir_localizacao(buscador, espera_curta)
    
    espera_media.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='accountId']"))).send_keys(cpf)
    
    espera_curta.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='enter-account-id']"))).click()
    
    espera_longa.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.EditText[@resource-id='password']"))).send_keys(senha)

    espera_curta.until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='submit-button']"))).click()

    popup_dois_fatores = espera_mensagem_dois_fatores(buscador)
    if popup_dois_fatores:
        espera_media.until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.CheckBox[@resource-id='confirmSkipMandatoryMfaCheckBox']"))).click()
        
        espera_media.until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.Button[@resource-id='confirmSkipMandatoryMfaButton']"))).click()
    
    tutorial_app(buscador, espera_media)

    cargos(buscador, espera_longa)
    
    todos_erros_anos, todos_erros_meses = processar_cargo_escolhido(buscador, espera_longa, espera_media)
    
    while perguntar_retry(todos_erros_anos, todos_erros_meses):
        print("Reiniciando para itens com erro...")
        todos_erros_anos, todos_erros_meses = processar_cargo_escolhido(buscador, espera_longa, espera_media)
       
if __name__ == "__main__":
        entrar_no_app()
