# Address information

## Endpoints

| Side | Method | Path | Body |
| --- | --- | --- | --- |
| Blockfrost | `GET` | `/addresses/{address}` | path param only |
| Koios | `POST` | `/address_info` | `{"_addresses": ["addr1..."]}` |

HTTP method and addressing style differ: Blockfrost is GET-by-path; Koios is POST with a batch of payment addresses.

## Field mapping

| Blockfrost field | Koios field | Class | Notes |
| --- | --- | --- | --- |
| `address` | `address` | Compatible | Bech32 payment address |
| `amount[].unit` / `amount[].quantity` | `balance` + `utxo_set[].asset_list` | Convert | Blockfrost aggregates per unit; Koios gives lovelace balance string plus UTxO assets |
| `stake_address` | `stake_address` | Compatible | Nullable |
| `script` | `script_address` | Rename | Boolean |
| `type` (`byron` / `shelley`) | — | Gap / Convert | Infer from address prefix in PoC |
| — | `utxo_set` | Gap (BF summary) | Blockfrost address summary omits full UTxO set; Koios includes it |
| — | batch `_addresses` | Convert | PoC translates the first address only |

## Amount conversion detail

Koios `balance` is total lovelace as a string. Blockfrost `amount` is an array of `{unit, quantity}` where lovelace uses `unit: "lovelace"` and native assets use `policy_id || asset_name` hex concatenation.

When mapping Koios -> Blockfrost:

1. Prefer aggregating `utxo_set` values and `asset_list` into Blockfrost `amount`.
2. If `utxo_set` is empty, fall back to `[{"unit":"lovelace","quantity": balance}]`.

When mapping Blockfrost -> Koios:

1. Extract lovelace quantity into `balance`.
2. Set `utxo_set` to `[]` (summary endpoint has no UTxOs). Native asset detail is a documented Gap unless another Blockfrost endpoint is queried later.

## Envelope conversion

| Direction | Conversion |
| --- | --- |
| Koios -> Blockfrost | Take first row of array; emit single object |
| Blockfrost -> Koios | Wrap object in a one-element array |

## Janus PoC behavior

- Blockfrost face: `GET /addresses/{address}` -> Koios `POST /address_info` with one address.
- Koios face: `POST /address_info` -> Blockfrost `GET /addresses/{address}` for the first requested address.
