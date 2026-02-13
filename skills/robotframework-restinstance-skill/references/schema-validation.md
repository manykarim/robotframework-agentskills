# JSON Schema Validation in RESTinstance

## Overview

RESTinstance supports JSON Schema validation for validating response structure and data types. This is powerful for API contract testing.

## Basic Schema Validation

### Inline Schema

```robotframework
GET    /users/1
Object    response body    {"type": "object", "required": ["id", "name"]}
```

### Schema From File

```robotframework
# Set expectation BEFORE the request
Expect Response Body    ${CURDIR}/schemas/user.json
GET    /users/1
```

## JSON Schema Basics

### Type Validation

```json
{
  "type": "object"      // object, array, string, integer, number, boolean, null
}
```

### Required Fields

```json
{
  "type": "object",
  "required": ["id", "name", "email"]
}
```

### Property Definitions

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "email": {"type": "string"},
    "active": {"type": "boolean"}
  }
}
```

## Complete Schema Examples

### User Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "email"],
  "properties": {
    "id": {
      "type": "integer",
      "minimum": 1
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "age": {
      "type": ["integer", "null"],
      "minimum": 0,
      "maximum": 150
    },
    "active": {
      "type": "boolean",
      "default": true
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": false
}
```

### Array Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "name"],
    "properties": {
      "id": {"type": "integer"},
      "name": {"type": "string"}
    }
  },
  "minItems": 0,
  "maxItems": 100
}
```

### Paginated Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["data", "meta"],
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/user"
      }
    },
    "meta": {
      "type": "object",
      "required": ["total", "page", "limit"],
      "properties": {
        "total": {"type": "integer", "minimum": 0},
        "page": {"type": "integer", "minimum": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100}
      }
    }
  },
  "definitions": {
    "user": {
      "type": "object",
      "required": ["id", "name"],
      "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"}
      }
    }
  }
}
```

## String Validation

### String Constraints

```json
{
  "type": "string",
  "minLength": 1,
  "maxLength": 255,
  "pattern": "^[A-Za-z]+$"
}
```

### String Formats

```json
{
  "type": "string",
  "format": "email"        // email address
}

{
  "type": "string",
  "format": "date-time"    // ISO 8601 date-time
}

{
  "type": "string",
  "format": "date"         // ISO 8601 date
}

{
  "type": "string",
  "format": "uri"          // URI
}

{
  "type": "string",
  "format": "uuid"         // UUID
}
```

### Enum Values

```json
{
  "type": "string",
  "enum": ["pending", "active", "inactive", "deleted"]
}
```

## Numeric Validation

### Integer Constraints

```json
{
  "type": "integer",
  "minimum": 1,
  "maximum": 1000,
  "exclusiveMinimum": 0,
  "multipleOf": 5
}
```

### Number Constraints

```json
{
  "type": "number",
  "minimum": 0.0,
  "maximum": 100.0,
  "exclusiveMaximum": 100.1
}
```

## Array Validation

### Array of Specific Type

```json
{
  "type": "array",
  "items": {
    "type": "string"
  }
}
```

### Array with Constraints

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id"]
  },
  "minItems": 1,
  "maxItems": 50,
  "uniqueItems": true
}
```

### Tuple Validation

```json
{
  "type": "array",
  "items": [
    {"type": "string"},
    {"type": "integer"},
    {"type": "boolean"}
  ],
  "additionalItems": false
}
```

## Object Validation

### Nested Objects

```json
{
  "type": "object",
  "properties": {
    "user": {
      "type": "object",
      "properties": {
        "profile": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "bio": {"type": "string"}
          }
        }
      }
    }
  }
}
```

### Pattern Properties

```json
{
  "type": "object",
  "patternProperties": {
    "^S_": {"type": "string"},
    "^I_": {"type": "integer"}
  },
  "additionalProperties": false
}
```

### Property Count

```json
{
  "type": "object",
  "minProperties": 1,
  "maxProperties": 10
}
```

## Conditional Schemas

### If-Then-Else

```json
{
  "type": "object",
  "if": {
    "properties": {"type": {"const": "company"}}
  },
  "then": {
    "required": ["company_name", "registration_number"]
  },
  "else": {
    "required": ["first_name", "last_name"]
  }
}
```

### OneOf

```json
{
  "oneOf": [
    {
      "type": "object",
      "properties": {
        "type": {"const": "email"},
        "address": {"type": "string", "format": "email"}
      }
    },
    {
      "type": "object",
      "properties": {
        "type": {"const": "phone"},
        "number": {"type": "string", "pattern": "^\\+?\\d{10,}$"}
      }
    }
  ]
}
```

### AnyOf

```json
{
  "anyOf": [
    {"type": "string"},
    {"type": "integer"}
  ]
}
```

## Using Schemas in Tests

### Validate Full Response

```robotframework
*** Test Cases ***
Validate User Response Schema
    # Set expectation BEFORE the request
    Expect Response Body    ${CURDIR}/schemas/user.json
    GET    /users/1
    Integer    response status    200
```

### Validate Nested Part

```robotframework
*** Test Cases ***
Validate User Profile Schema
    # Note: Expect Response Body validates the full response body.
    # For nested validation, use inline schema with Object keyword.
    GET    /users/1
    Object    response body profile    ${CURDIR}/schemas/profile.json
```

### Validate Array Items

```robotframework
*** Test Cases ***
Validate Users List Schema
    # Set expectation BEFORE the request
    Expect Response Body    ${CURDIR}/schemas/users-list.json
    GET    /users
    Array    response body
```

### Inline Schema for Quick Checks

```robotframework
*** Test Cases ***
Quick Schema Check
    GET    /users/1
    Object    response body    {"type": "object", "required": ["id", "name", "email"]}
```

## Schema File Organization

### Recommended Structure

```
schemas/
    common/
        address.json
        pagination.json
    users/
        user.json
        user-list.json
        user-create.json
        user-update.json
    orders/
        order.json
        order-list.json
```

### Schema with References

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "user": {"$ref": "common/user.json"},
    "address": {"$ref": "common/address.json"}
  }
}
```

## Practical Examples

### API Contract Test

```robotframework
*** Settings ***
Library    REST    https://api.example.com

*** Test Cases ***
User API Contract
    [Documentation]    Verify User API follows contract
    [Tags]    contract    schema

    # GET user
    Expect Response Body    ${CURDIR}/schemas/user.json
    GET    /users/1
    Integer    response status    200

    # GET users list
    Expect Response Body    ${CURDIR}/schemas/user-list.json
    GET    /users
    Integer    response status    200

    # POST user
    Expect Response Body    ${CURDIR}/schemas/user.json
    POST    /users    {"name": "Test", "email": "test@test.com"}
    Integer    response status    201
```

### Error Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["error"],
  "properties": {
    "error": {
      "type": "object",
      "required": ["code", "message"],
      "properties": {
        "code": {"type": "string"},
        "message": {"type": "string"},
        "details": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "field": {"type": "string"},
              "message": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

### Validate Error Response

```robotframework
*** Test Cases ***
Validate Error Response Schema
    Expect Response Body    ${CURDIR}/schemas/error.json
    POST    /users    {"invalid": "data"}
    Integer    response status    400
    String    response body error code
    String    response body error message
```
