from decimal import Decimal

_ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
]
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _two_digit_words(n):
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f'-{_ONES[ones]}' if ones else '')


def _three_digit_words(n):
    if n >= 100:
        rest = n % 100
        head = f'{_ONES[n // 100]} Hundred'
        return head + (f' And {_two_digit_words(rest)}' if rest else '')
    return _two_digit_words(n)


def amount_in_words_inr(amount):
    """Convert a rupee amount to words using the Indian numbering system
    (Lakh/Crore rather than Million/Billion), matching how Indian tax
    invoices print the 'Amount in Words' line.

    amount_in_words_inr(6297) -> 'Six Thousand Two Hundred And Ninety-Seven Rupees Only'
    """
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    rupees = int(amount)
    paise = int((amount - rupees) * 100)

    if rupees == 0:
        rupee_words = 'Zero'
    else:
        parts = []
        remainder = rupees
        crore, remainder = divmod(remainder, 10000000)
        lakh, remainder = divmod(remainder, 100000)
        thousand, remainder = divmod(remainder, 1000)
        hundred = remainder

        if crore:
            parts.append(f'{_three_digit_words(crore)} Crore')
        if lakh:
            parts.append(f'{_three_digit_words(lakh)} Lakh')
        if thousand:
            parts.append(f'{_three_digit_words(thousand)} Thousand')
        if hundred:
            parts.append(_three_digit_words(hundred))
        rupee_words = ' '.join(parts)

    words = f'{rupee_words} Rupees'
    if paise:
        words += f' And {_two_digit_words(paise)} Paise'
    return words + ' Only'
