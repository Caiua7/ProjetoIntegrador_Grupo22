import assert from 'node:assert/strict'
import test from 'node:test'
import {
  editavel,
  hojeIso,
  margemParaApi,
  moedaValida,
  taxaComMargem,
  taxaParaApi,
  valorParametroParaApi,
  valorParametroParaTela,
  vigentesPorChave,
} from './parametrosRules.ts'

test('vigente por moeda é a data mais recente até a referência', () => {
  const registros = [
    { moeda: 'USD', data: '2026-11-01', taxa: '5.1' },
    { moeda: 'USD', data: '2026-11-05', taxa: '5.3' },
    { moeda: 'USD', data: '2026-11-10', taxa: '5.5' },
    { moeda: 'EUR', data: '2026-10-01', taxa: '6.0' },
  ]
  const vigentes = vigentesPorChave(registros, (r) => r.moeda, (r) => r.data, '2026-11-06')
  assert.deepEqual([...vigentes.keys()], ['EUR', 'USD'])
  assert.equal(vigentes.get('USD').taxa, '5.3')
  assert.equal(vigentesPorChave(registros, (r) => r.moeda, (r) => r.data, '2026-09-01').size, 0)
})

test('só hoje em diante é editável, como no trigger do banco', () => {
  assert.equal(editavel('2026-11-06', '2026-11-06'), true)
  assert.equal(editavel('2026-11-07', '2026-11-06'), true)
  assert.equal(editavel('2026-11-05', '2026-11-06'), false)
})

test('hoje em ISO usa a data local', () => {
  assert.equal(hojeIso(new Date(2026, 0, 3, 23, 59)), '2026-01-03')
})

test('taxa com margem é exata', () => {
  assert.equal(taxaComMargem('5.123400', '0.020000'), '5.225868')
  assert.equal(taxaComMargem('5', '0'), '5')
})

test('parâmetro percentual trafega em fração e o prazo em dias', () => {
  assert.equal(valorParametroParaApi('perda_percentual', '1,2'), '0.012')
  assert.equal(valorParametroParaApi('perda_percentual', '100'), '1')
  assert.equal(valorParametroParaApi('perda_percentual', '100.01'), null)
  assert.equal(valorParametroParaApi('perda_percentual', '-1'), null)
  assert.equal(valorParametroParaApi('perda_percentual', '1.23456'), null)
  assert.equal(valorParametroParaApi('prazo_medio_padrao_dias', '45'), '45')
  assert.equal(valorParametroParaApi('prazo_medio_padrao_dias', '45.5'), null)
  assert.equal(valorParametroParaTela('perda_percentual', '0.012000'), '1.2')
  assert.equal(valorParametroParaTela('prazo_medio_padrao_dias', '45.000000'), '45')
})

test('margem de segurança em % vira fração e vazio é zero', () => {
  assert.equal(margemParaApi('2'), '0.02')
  assert.equal(margemParaApi(''), '0')
  assert.equal(margemParaApi('101'), null)
})

test('taxa precisa ser positiva e caber em NUMERIC(14,6)', () => {
  assert.equal(taxaParaApi('5,1234'), '5.1234')
  assert.equal(taxaParaApi('0'), null)
  assert.equal(taxaParaApi('0.0000001'), null)
  assert.equal(taxaParaApi('123456789'), null)
})

test('moeda é código ISO de 3 letras e nunca BRL', () => {
  assert.equal(moedaValida('USD'), true)
  assert.equal(moedaValida('BRL'), false)
  assert.equal(moedaValida('usd'), false)
})
