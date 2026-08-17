import asyncio
import time
from collections import deque


class AsyncTokenBucketLimiter:
    """
    Controlador de vazão assíncrono baseado em janela deslizante (Sliding Window) de 60 segundos.
    Controla simultaneamente:
    - RPM (Requests Per Minute): número máximo de requisições por janela.
    - TPM (Tokens Per Minute): volume máximo de tokens por janela.
    """

    def __init__(
        self,
        max_rpm: int = 300,
        max_tpm: int = 1_000_000,
        window_seconds: float = 60.0,
    ) -> None:
        self._max_rpm = max(1, max_rpm)
        self._max_tpm = max(1, max_tpm)
        self._window = max(0.1, window_seconds)
        self._requests: deque[float] = deque()
        self._token_events: deque[tuple[float, int]] = deque()
        self._current_tokens: int = 0
        self._lock = asyncio.Lock()

    @property
    def max_rpm(self) -> int:
        return self._max_rpm

    @property
    def max_tpm(self) -> int:
        return self._max_tpm

    @property
    def current_rpm_usage(self) -> int:
        return len(self._requests)

    @property
    def current_tpm_usage(self) -> int:
        return self._current_tokens

    async def acquire(self, estimated_tokens: int = 1) -> None:
        """
        Adquire cota para 1 requisição com estimated_tokens.
        Se a cota de RPM ou TPM estiver cheia, aguarda não-bloqueante até liberar slot.
        """
        tokens = max(1, estimated_tokens)
        async with self._lock:
            while True:
                now = time.monotonic()

                # 1. Purga requisições fora da janela deslizante
                while self._requests and now - self._requests[0] >= self._window:
                    self._requests.popleft()

                # 2. Purga tokens fora da janela deslizante
                while self._token_events and now - self._token_events[0][0] >= self._window:
                    _, old_tokens = self._token_events.popleft()
                    self._current_tokens = max(0, self._current_tokens - old_tokens)

                # 3. Verifica se cabe no orçamento da janela atual
                if (
                    len(self._requests) < self._max_rpm
                    and self._current_tokens + tokens <= self._max_tpm
                ):
                    self._requests.append(now)
                    self._token_events.append((now, tokens))
                    self._current_tokens += tokens
                    return

                # 4. Calcula tempo mínimo de espera até o slot mais antigo expirar
                oldest_req = self._requests[0] if self._requests else now
                oldest_tok = self._token_events[0][0] if self._token_events else now
                earliest_event = min(oldest_req, oldest_tok)
                sleep_time = max(0.01, (earliest_event + self._window) - now)

                # Libera o lock momentaneamente para permitir que outras corrotinas rodem
                await asyncio.sleep(sleep_time)
