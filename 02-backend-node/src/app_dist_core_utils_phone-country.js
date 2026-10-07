import { parsePhoneNumber } from 'libphonenumber-js';
export function parseCountryFromPhone(phone) {
    if (!phone)
        return '';
    try {
        const normalized = phone.startsWith('+') ? phone : '+' + phone;
        const parsed = parsePhoneNumber(normalized);
        return parsed?.country || '';
    }
    catch {
        return '';
    }
}
//# sourceMappingURL=phone-country.js.map