import { es } from './es';

export const translations = { es };
export type Locale = keyof typeof translations;
export const defaultLocale: Locale = 'es';

export function getTranslations(locale: Locale = defaultLocale) {
  return translations[locale] || translations[defaultLocale];
}
