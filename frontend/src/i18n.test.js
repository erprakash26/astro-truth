// Pure-logic test for the "Other" language UI-chrome swap, using Node's
// built-in test runner -- no new frontend test framework/dependency, just
// `node --test` against this module's exported functions (see
// backend/tests/test_ui_translation.py for the data-layer half of this).
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { setOtherTranslations, t } from './i18n.js'

test('t() falls back to English for lang "other" before any translation is applied', () => {
  setOtherTranslations(null)
  assert.equal(t('other', 'submit'), t('en', 'submit'))
})

test('setOtherTranslations() makes t() return the translated string for lang "other"', () => {
  setOtherTranslations({ submit: 'Generar carta', appName: 'AstroTruth' })
  assert.equal(t('other', 'submit'), 'Generar carta')
  assert.equal(t('other', 'appName'), 'AstroTruth')
})

test('t() falls back to English for any key missing from the applied translation', () => {
  setOtherTranslations({ submit: 'Generar carta' })
  assert.equal(t('other', 'tagline'), t('en', 'tagline'))
})

test('setOtherTranslations(null) clears a previously applied translation', () => {
  setOtherTranslations({ submit: 'Generar carta' })
  assert.equal(t('other', 'submit'), 'Generar carta')

  setOtherTranslations(null)
  assert.equal(t('other', 'submit'), t('en', 'submit'))
})
