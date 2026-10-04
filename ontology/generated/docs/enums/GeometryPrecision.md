---
search:
  boost: 2.0
---


# Enum: GeometryPrecision 




_How precisely a stored geometry locates its subject (§14.2, SIG-IDENT-004). An agency-registry latitude/longitude MUST be stored as `organization_centroid_or_unknown` and MUST NOT be used for point-in-polygon jurisdiction assignment or as an organization address — using an agency centroid as a device location would be a fabrication._



<div data-search-exclude markdown="1">

URI: [sig:enum/GeometryPrecision](https://ontology.sig-project.org/schema/enum/GeometryPrecision)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| rooftop | None | A rooftop / address-point geocode |
| parcel_centroid | None | The centroid of a matched parcel |
| street_interpolated | None | Interpolated along a street segment |
| place_centroid | None | The centroid of a containing place; coarse |
| organization_centroid_or_unknown | None | An agency-registry point of unknown precision; barred from point-in-polygon a... |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: GeometryPrecision
description: How precisely a stored geometry locates its subject (§14.2, SIG-IDENT-004).
  An agency-registry latitude/longitude MUST be stored as `organization_centroid_or_unknown`
  and MUST NOT be used for point-in-polygon jurisdiction assignment or as an organization
  address — using an agency centroid as a device location would be a fabrication.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  rooftop:
    text: rooftop
    description: A rooftop / address-point geocode.
  parcel_centroid:
    text: parcel_centroid
    description: The centroid of a matched parcel.
  street_interpolated:
    text: street_interpolated
    description: Interpolated along a street segment.
  place_centroid:
    text: place_centroid
    description: The centroid of a containing place; coarse.
  organization_centroid_or_unknown:
    text: organization_centroid_or_unknown
    description: An agency-registry point of unknown precision; barred from point-in-polygon
      and address use (SIG-IDENT-004).

```
</details>

</div>