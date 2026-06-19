const OPERATOR_TOKEN_KEY = 'clear_operator_token';

export function getOperatorToken(): string | null {
  return sessionStorage.getItem(OPERATOR_TOKEN_KEY);
}

export function setOperatorToken(token: string): void {
  sessionStorage.setItem(OPERATOR_TOKEN_KEY, token);
}

export function clearOperatorToken(): void {
  sessionStorage.removeItem(OPERATOR_TOKEN_KEY);
}

export function isOperatorAuthed(): boolean {
  return !!getOperatorToken();
}
