describe('Fluxo completo do sistema', () => {
  const uniqueEmail = `testuser_${Date.now()}@exemplo.com`
  const password = 'senha123'

  const adminEmail = `admin_${uniqueEmail}`
  const managerEmail = `manager_${uniqueEmail}`
  const operatorEmail = `operator_${uniqueEmail}`

  let token = ''
  let automationName = `Auto Cypress ${Date.now()}`
  let automationId = ''

  // Helper para logar como admin SEM depender de testes anteriores
  function loginAsAdmin() {
    cy.visit('/login')
    cy.get('input#email').type(adminEmail)
    cy.get('input#password').type(password)
    cy.get('button[type="submit"]').click()
    cy.location('pathname', { timeout: 8000 }).should('eq', '/')
  }

  it('deve registrar novo usuário (admin)', () => {
    cy.visit('/register')
    cy.get('input#name').type('Usuário Admin E2E')
    cy.get('input#email').type(adminEmail)
    cy.get('input#password').type(password)
    cy.get('select#role').select('admin')

    // Para admin, setor NÃO deve ser exibido
    cy.get('select#sector').should('not.exist')

    cy.get('button[type="submit"]').click()
    cy.contains('Cadastro realizado com sucesso!', { timeout: 8000 })
    cy.url().should('not.include', '/register')
  })

  it('deve registrar novo usuário (manager)', () => {
    cy.visit('/register')
    cy.get('input#name').type('Usuário Manager E2E')
    cy.get('input#email').type(managerEmail)
    cy.get('input#password').type(password)
    cy.get('select#role').select('manager')

    cy.get('select#sector', { timeout: 8000 })
      .should('be.visible')
      .and('not.be.disabled')

    cy.get('select#sector')
      .find('option')
      .then($options => {
        if ($options.length <= 1) {
          throw new Error(
            'Nenhum setor cadastrado no backend (/sectors/ retornou lista vazia). ' +
            'Sem setor não é possível registrar manager/operator. ' +
            'Crie setores no banco antes de rodar esse teste.'
          )
        }

        const secondOption = $options.eq(1)
        const value = secondOption.val()
        cy.get('select#sector').select(value)
      })

    cy.get('button[type="submit"]').click()
    cy.contains('Cadastro realizado com sucesso!', { timeout: 8000 })
    cy.url().should('not.include', '/register')
  })

  it('deve registrar novo usuário (operator)', () => {
    cy.visit('/register')
    cy.get('input#name').type('Usuário Operator E2E')
    cy.get('input#email').type(operatorEmail)
    cy.get('input#password').type(password)
    cy.get('select#role').select('operator')

    cy.get('select#sector', { timeout: 8000 })
      .should('be.visible')
      .and('not.be.disabled')

    cy.get('select#sector')
      .find('option')
      .then($options => {
        if ($options.length <= 1) {
          throw new Error(
            'Nenhum setor cadastrado no backend (/sectors/ retornou lista vazia). ' +
            'Sem setor não é possível registrar manager/operator. ' +
            'Crie setores no banco antes de rodar esse teste.'
          )
        }

        const secondOption = $options.eq(1)
        const value = secondOption.val()
        cy.get('select#sector').select(value)
      })

    cy.get('button[type="submit"]').click()
    cy.contains('Cadastro realizado com sucesso!', { timeout: 8000 })
    cy.url().should('not.include', '/register')
  })

  it('deve logar como admin recém-criado', () => {
    loginAsAdmin()

    // Mesmo sabendo que o Cypress limpa depois, aqui a gente só valida que o login funciona
    cy.window().then(win => {
      token = win.localStorage.getItem('token')
      expect(token, 'token salvo no localStorage').to.exist
    })
  })

  it('deve criar automação de dashboard', () => {
    // Cada teste começa “limpo”, então loga de novo
    loginAsAdmin()

    cy.contains(/Portal de Automação/i, { timeout: 8000 })

    // Procura um botão com "adicionar" e "automa" no texto
    cy.contains('button', /adicionar.*automa/i, { timeout: 8000 }).click()

    cy.get('input#name').type(automationName)
    cy.get('select#automation_type').select('Dashboard')

    cy.get('input#module_path', { timeout: 5000 })
      .should('have.value', 'modules.comercial.dashboard.run_dashboard_v2')

    cy.get('input#func_name').clear().type('main')

    // Esses arquivos PRECISAM existir em cypress/fixtures
    cy.get('input#dashboard_screenshot').selectFile('cypress/fixtures/dashboard_screenshot.png', { force: true })
    cy.get('input#dashboard_name_image').selectFile('cypress/fixtures/dashboard_name_image.png', { force: true })

    cy.get('input[type="checkbox"][value="diario"]').check()
    cy.get('input[type="checkbox"][value="mensal"]').check()
    cy.get('input[type="checkbox"][value="anual"]').check()

    cy.get('button[type="submit"]').click()
    cy.contains(`Automação "${automationName}" criada com sucesso!`, { timeout: 8000 })
    cy.contains(automationName, { timeout: 8000 })
  })

  it('deve agendar automação', () => {
    loginAsAdmin()

    cy.contains(automationName, { timeout: 8000 }).parents('.card').within(() => {
      cy.contains('Agendar').click()
    })

    cy.get('.modal-box').within(() => {
      cy.get('select').first().select('Segunda')
      cy.get('input[type="time"]').type('07:30')
      cy.get('input[type="number"]').clear().type('5')
      cy.contains('Salvar').click()
      cy.contains('Agendado com sucesso.', { timeout: 5000 })
      cy.contains('Cancelar').click()
    })
  })

  it('deve executar automação', () => {
    loginAsAdmin()

    cy.contains(automationName, { timeout: 8000 }).parents('.card').within(() => {
      cy.contains('Executar').click()
    })
    cy.contains('Execução enfileirada', { timeout: 8000 })
  })

  it('deve listar execuções', () => {
    loginAsAdmin()

    cy.visit('/runs')
    cy.contains(automationName, { timeout: 8000 })
  })

  it('deve abrir tela de dashboards', () => {
    loginAsAdmin()

    cy.visit('/dashboards')
    cy.contains('Gerenciar Dashboards', { timeout: 8000 })
  })

  it('deve acessar dashboard principal', () => {
    loginAsAdmin()

    cy.visit('/dashboard')
    cy.contains('Portal de Automação', { timeout: 8000 })
  })
})
