function withoutCyr(input) {
  const value = input.value;
    const re = /[а-яё]/gi;
  input.value = value.replace(re, '');
}