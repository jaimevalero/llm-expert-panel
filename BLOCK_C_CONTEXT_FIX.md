# Mejoras al Manejo de Contexto en Block C

## Problema Identificado

Al ejecutar el experimento completo, Block C fallaba para el modelo **phi4** con el siguiente error:

```
Error code: 400 - This endpoint's maximum context length is 16384 tokens. 
However, you requested about 22763 tokens (21263 of text input, 1500 in the output).
```

### Causa Raíz

1. **Block C requiere contexto previo**: El prompt de Block C dice explícitamente "You have read all the responses from the other models"
2. **Sin contexto anterior**: El código original NO pasaba las respuestas de Block A y B
3. **Implementación inicial**: Se agregó contexto completo sin considerar límites por modelo
4. **phi4 tiene contexto limitado**: Solo soporta 16K tokens vs 32K+ de otros modelos

## Soluciones Implementadas

### 1. Configuración de Límites de Contexto por Modelo

**Archivo: [src/config.py](src/config.py)**

- Agregado campo `max_context_tokens` a `ModelConfig`
- Carga desde variable de entorno `MODEL_N_MAX_CONTEXT`
- Default: 32,000 tokens si no se especifica

**Archivo: [.env.test](.env.test)**

Límites configurados para cada modelo:
- `phi4`: 16,384 tokens (LIMITADO) ⚠️
- `deepseek`: 32,768 tokens
- `qwen3`: 32,768 tokens
- `llama33`: 131,072 tokens

### 2. Compresión Inteligente de Contexto

**Archivo: [src/orchestrator.py](src/orchestrator.py)**

#### Método `_construct_block_c_prompt()` mejorado

```python
# Calcula tokens disponibles por modelo
max_context = model_config.max_context_tokens
max_output = block_prompt.max_tokens

# Reserva: 30% para prompt base, 70% para contexto
available_for_context = int((max_context - max_output) * 0.7)
```

#### Nuevo método `_build_compressed_context()`

Estrategia de compresión:
1. **Estimación de tokens**: ~4 caracteres por token
2. **Distribución equitativa**: Divide espacio disponible entre todas las respuestas
3. **Límites dinámicos**: Entre 200-600 caracteres por respuesta según disponibilidad
4. **Truncamiento inteligente**: Mantiene inicio de cada respuesta + "..."

**Ejemplo para phi4:**
- Contexto máximo: 16,384 tokens
- Output reservado: 1,500 tokens
- Disponible para entrada: ~14,884 tokens
- 70% para contexto previo: ~10,419 tokens
- Con ~30 respuestas de A+B: ~347 caracteres por respuesta

### 3. Inyección de Contexto Solo en Block C

El código ahora diferencia:

```python
# Block C needs special handling - inject A/B context
if current_block == "C":
    model_prompt = self._construct_block_c_prompt(
        model_name=model_name,
        block_prompt=block_prompt,
        state=state,
        question=question
    )
else:
    # Blocks A, B, D: No previous context needed
    question_prompt = self._construct_question_prompt(
        state["common_instructions"],
        block_prompt,
        question
    )
```

## Verificación

### 1. Verificar límites de contexto se cargan correctamente

```bash
python -c "
from src.config import Config
config = Config.load('.env.test')
for name, model in config.models.items():
    print(f'{name}: {model.max_context_tokens:,} tokens')
"
```

**Output esperado:**
```
deepseek: 32,768 tokens
phi4: 16,384 tokens
qwen3: 32,768 tokens
llama33: 131,072 tokens
```

### 2. Ejecutar experimento completo

```bash
python src/main.py --env-file .env.test --blocks A B C
```

### 3. Verificar que Block C menciona contexto previo

```bash
# Ver output de Block C
cat output/*/Block_C_Questions_Answers.md
```

Las respuestas deberían referenciar específicamente observaciones de bloques A y B.

## Métricas de Éxito

✅ **Antes**: Block C fallaba con error 400 para phi4  
✅ **Después**: Block C completa exitosamente para todos los modelos

✅ **Antes**: Contexto de A/B no se pasaba  
✅ **Después**: Contexto comprimido se incluye dinámicamente

✅ **Antes**: Mismo prompt para todos los modelos  
✅ **Después**: Prompt ajustado según capacidad de cada modelo

## Costo Estimado

Con los 4 modelos ultra-baratos de `.env.test`:

- **Block A**: ~$0.002-0.005 (< 1 centavo)
- **Block B**: ~$0.002-0.005 (< 1 centavo)
- **Block C**: ~$0.005-0.010 (< 1 centavo) - Más contexto
- **Block D**: ~$0.002-0.005 (< 1 centavo)

**Total experimento completo: ~$0.01-0.02 (1-2 centavos)**

## Alternativas Consideradas

### Opción 1: Resumir con otro modelo ❌
Agregar paso previo para resumir A+B con un modelo barato. 
- **Problema**: Complejidad adicional, costo extra, pérdida de detalle

### Opción 2: Pasar archivo de contexto ❌
Guardar A+B en archivo y referenciar en prompt.
- **Problema**: OpenRouter no soporta lectura de archivos

### Opción 3: Excluir modelos de contexto limitado ❌
Solo ejecutar Block C en modelos con >32K tokens.
- **Problema**: Reduce diversidad del panel

### Opción 4 (IMPLEMENTADA): Compresión dinámica ✅
Ajustar cantidad de contexto según capacidad del modelo.
- **Ventajas**: Todos los modelos participan, sin pasos adicionales
- **Desventajas**: Algunos modelos reciben menos contexto

## Próximos Pasos Opcionales

### Mejora Futura 1: Extracción de puntos clave
En lugar de truncar, usar regex/NLP para extraer:
- Posiciones filosóficas principales
- Argumentos clave
- Puntos de desacuerdo

### Mejora Futura 2: Priorización de contenido
Dar más espacio a:
- Respuestas del mismo modelo (para continuidad)
- Respuestas de Round 3 (conclusiones)
- Argumentos más citados por otros

### Mejora Futura 3: Notificación al usuario
```
⚠️  phi4 has limited context (16K). Context compressed to 200 chars/response.
✓  llama33 has large context (131K). Full responses included.
```

## Testing

Pruebas recomendadas:

```bash
# 1. Solo Block C (debe fallar sin A/B previo)
python src/main.py --env-file .env.test --block C

# 2. A + C (debe usar contexto de A)
python src/main.py --env-file .env.test --blocks A C

# 3. Experimento completo
python src/main.py --env-file .env.test

# 4. Verificar logs de compresión
grep "compressed" output/*/logs/*.log
```

## Referencias

- [OpenRouter Models](https://openrouter.ai/models)
- [Prompt de Block C](experiment3/prompts/Block_C_Round_1.md)
- [Instrucciones Comunes](experiment3/prompts/common_instructions.md)
