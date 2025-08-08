import time
import selenium.webdriver as webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as Ec

buscador = webdriver.Chrome()
buscador.get("https://google.com")

def esperas_de_elementos():
    espera_curta = WebDriverWait(buscador, 20)
    espera_media = WebDriverWait(buscador, 40)
    espera_longa = WebDriverWait(buscador, 60)

    return espera_curta, espera_media, espera_longa

def login_gov_br():
    login = input("Digite o login do usuário: ") 
    senha = input("Digite a senha do usuário: ")

    return login, senha

#def captcha():
    

def entrar_no_sistema():
    espera_curta, espera_media, espera_longa = esperas_de_elementos()
    login, senha = login_gov_br()

    espera_media.until(
        Ec.element_to_be_clickable((By.XPATH, "//*[@id='accountId']"))).send_keys(login)
    
    espera_curta.until(
        Ec.element_to_be_clickable((By.XPATH, "//*[@id='enter-account-id']"))).click()
    
    espera_media.until(
        Ec.element_to_be_clickable((By.XPATH, "//input[contains(@onkeypress, 'submitOnEnterKeyPress')]"))).send_keys(senha)

    espera_curta.until(
        Ec.element_to_be_clickable((By.XPATH, "//button[@id='submit-button']"))).click()

    time.sleep(10)

if __name__ == "__main__":
    entrar_no_sistema()