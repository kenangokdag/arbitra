# Evidence & Provider Spec

## Amaç

Arbitra'nın literatür, atıf ve kanıt katmanı tek bir providera bağımlı olmamalı; OpenAlex, Crossref, Semantic Scholar, PubMed veya gelecekteki kaynaklar adapter olarak eklenebilmelidir.

## Provider Protocol

```python
class ScholarlyProvider(Protocol):
    name: str
    version: str

    async def search_works(self, query: ScholarlySearchQuery) -> list[Work]: ...
    async def resolve_reference(self, reference: RawReference) -> ResolvedReference: ...
    async def get_work(self, work_id: str) -> Work | None: ...
    async def get_references(self, work_id: str) -> list[CitationEdge]: ...
    async def get_citations(self, work_id: str) -> list[CitationEdge]: ...
```

## ProviderSnapshot

Her provider çağrısı rapor provenance'a şu şekilde kaydedilir:

```json
{
  "provider": "openalex",
  "provider_version": "2026-06",
  "query_hash": "...",
  "request_time": "...",
  "status": "ok | degraded | failed | rate_limited | auth_missing",
  "result_count": 42,
  "cache_hit": false,
  "limitations": ["abstract only"]
}
```

## Support levels

```text
full_text_verified: Tam metin veya açık full-text kaynakla doğrulandı.
abstract_only: Sadece abstract/metadata düzeyinde doğrulandı.
metadata_only: Sadece başlık/yazar/yıl/doi gibi metadata var.
unresolved: Kaynak çözülemedi.
contradictory: Kaynak iddiayı desteklemek yerine çelişiyor gibi görünüyor.
not_applicable: Bu iddia citation gerektirmiyor.
```

## Citation integrity rules

- Kaynak çözülmediğinde sistem kaynak uydurmaz.
- Abstract-only kontrol full-text gibi sunulmaz.
- Claim strength ile citation context uyumsuzsa severity artar.
- Unverified citation critique confidence düşük/orta kalır.
- Kaynak bulma başarısızlığı akademik hüküm değil, evidence limitation olarak raporlanır.

## Provider error mapping

| Provider error | Domain behavior |
|---|---|
| auth missing | feature degraded veya production config fail, fake result yok |
| rate limited | retry/backoff, sonra degraded |
| timeout | retry, sonra degraded |
| malformed response | provider failed, schema alert |
| not found | unresolved reference |

## Caching

Cache key:

```text
provider + endpoint + normalized query + provider version
```

Cache result provenance’da `cache_hit` olarak görünür.

## Başarı kapısı

- Business logic raw provider URL bilmez.
- Her evidence result provider ve confidence taşır.
- Provider failure sessiz boş liste değildir.
- Citation critique support level gösterir.
