"""
Tool definitions for the AI Tax Assistant.
These tools allow the LLM to invoke KudiCore engine functions during conversation.
Each tool has a schema (for the LLM) and an execute function (for the backend).
"""

import json
from dataclasses import asdict

from app.core.tax_rules.pit import PITCalculator, Deductions
from app.core.tax_rules.cit import CITCalculator
from app.core.tax_rules.vat import VATCalculator
from app.core.tax_rules.wht import WHTCalculator, WHTPaymentType, RecipientType
from app.core.currency import CurrencyEngine
from app.core.classifier import TransactionClassifier
from app.core.scenario import ScenarioModeler


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_pit",
            "description": "Calculate Nigerian Personal Income Tax (PIT) for an individual based on the Nigeria Tax Act 2025. Returns tax liability, effective rate, and bracket breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_income": {
                        "type": "number",
                        "description": "Annual gross income in Naira (₦)",
                    },
                    "pension": {
                        "type": "number",
                        "description": "Annual pension contribution in Naira",
                        "default": 0,
                    },
                    "nhf": {
                        "type": "number",
                        "description": "Annual National Housing Fund contribution in Naira",
                        "default": 0,
                    },
                    "nhis": {
                        "type": "number",
                        "description": "Annual National Health Insurance contribution in Naira",
                        "default": 0,
                    },
                    "life_insurance": {
                        "type": "number",
                        "description": "Annual life insurance premium in Naira",
                        "default": 0,
                    },
                    "housing_loan_interest": {
                        "type": "number",
                        "description": "Annual housing loan interest in Naira",
                        "default": 0,
                    },
                    "annual_rent_paid": {
                        "type": "number",
                        "description": "Annual rent paid in Naira (20% relief, max ₦500,000)",
                        "default": 0,
                    },
                    "is_minimum_wage": {
                        "type": "boolean",
                        "description": "Whether the person earns minimum wage (exempt from PIT)",
                        "default": False,
                    },
                },
                "required": ["gross_income"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_cit",
            "description": "Calculate Nigerian Company Income Tax (CIT) for a business. Small companies (turnover ≤ ₦25M) pay 0%, others pay 30%. Includes development levy calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_profit": {
                        "type": "number",
                        "description": "Gross profit of the company in Naira",
                    },
                    "allowable_deductions": {
                        "type": "number",
                        "description": "Total allowable deductions in Naira",
                        "default": 0,
                    },
                    "annual_turnover": {
                        "type": "number",
                        "description": "Annual turnover/revenue in Naira (used to classify company size)",
                        "default": 0,
                    },
                    "is_mne": {
                        "type": "boolean",
                        "description": "Whether the company is part of a multinational enterprise group",
                        "default": False,
                    },
                },
                "required": ["gross_profit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_vat",
            "description": "Calculate Nigerian Value Added Tax (VAT) at 7.5% on taxable supplies. Handles exempt and zero-rated supplies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount of the taxable supply in Naira",
                    },
                    "is_inclusive": {
                        "type": "boolean",
                        "description": "Whether the amount already includes VAT",
                        "default": False,
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_wht",
            "description": "Calculate Nigerian Withholding Tax (WHT) on a payment. Rates vary by payment type and recipient type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_amount": {
                        "type": "number",
                        "description": "Gross payment amount in Naira",
                    },
                    "payment_type": {
                        "type": "string",
                        "description": "Type of payment",
                        "enum": ["dividend", "interest", "rent", "royalty", "commission", "consultancy", "professional_fees", "technical_fees", "management_fees", "construction", "supply_of_goods", "contract", "directors_fees"],
                    },
                    "recipient_type": {
                        "type": "string",
                        "description": "Whether the recipient is an individual or company",
                        "enum": ["individual", "company"],
                        "default": "company",
                    },
                },
                "required": ["gross_amount", "payment_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify_transaction",
            "description": "Classify a financial transaction as income, expense, or capital. Determines tax relevance (VAT, WHT applicability).",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the transaction",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount",
                    },
                    "is_credit": {
                        "type": "boolean",
                        "description": "Whether money was received (true) or paid out (false)",
                        "default": True,
                    },
                },
                "required": ["description", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert a foreign currency amount to Nigerian Naira (NGN) using CBN official exchange rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount in the source currency",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Source currency code",
                        "enum": ["USD", "GBP", "EUR"],
                    },
                },
                "required": ["amount", "currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_scenario",
            "description": "Model a 'what-if' tax scenario. Compare current vs projected tax liability based on income changes, deduction changes, or individual vs company filing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_type": {
                        "type": "string",
                        "description": "Type of scenario to model",
                        "enum": ["income_change", "deduction_impact", "individual_vs_company"],
                    },
                    "current_income": {
                        "type": "number",
                        "description": "Current annual gross income in Naira",
                    },
                    "projected_income": {
                        "type": "number",
                        "description": "Projected annual gross income in Naira (for income_change scenario)",
                    },
                },
                "required": ["scenario_type", "current_income"],
            },
        },
    },
]


pit_calc = PITCalculator()
cit_calc = CITCalculator()
vat_calc = VATCalculator()
wht_calc = WHTCalculator()
currency_engine = CurrencyEngine()
classifier = TransactionClassifier()
scenario_modeler = ScenarioModeler()


def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        if tool_name == "calculate_pit":
            deductions = Deductions(
                pension=arguments.get("pension", 0),
                nhf=arguments.get("nhf", 0),
                nhis=arguments.get("nhis", 0),
                life_insurance=arguments.get("life_insurance", 0),
                housing_loan_interest=arguments.get("housing_loan_interest", 0),
                annual_rent_paid=arguments.get("annual_rent_paid", 0),
            )
            result = pit_calc.calculate(
                gross_income=arguments["gross_income"],
                deductions=deductions,
                is_minimum_wage_earner=arguments.get("is_minimum_wage", False),
            )
            return json.dumps(asdict(result), default=str)

        elif tool_name == "calculate_cit":
            result = cit_calc.calculate(
                gross_profit=arguments["gross_profit"],
                allowable_deductions=arguments.get("allowable_deductions", 0),
                annual_turnover=arguments.get("annual_turnover", 0),
                is_mne=arguments.get("is_mne", False),
            )
            return json.dumps(asdict(result), default=str)

        elif tool_name == "calculate_vat":
            if arguments.get("is_inclusive", False):
                result = vat_calc.extract_vat_from_inclusive(arguments["amount"])
            else:
                result = vat_calc.calculate_simple(arguments["amount"])
            return json.dumps(result)

        elif tool_name == "calculate_wht":
            result = wht_calc.calculate_single(
                gross_amount=arguments["gross_amount"],
                payment_type=WHTPaymentType(arguments["payment_type"]),
                recipient_type=RecipientType(arguments.get("recipient_type", "company")),
            )
            return json.dumps(asdict(result), default=str)

        elif tool_name == "classify_transaction":
            result = classifier.classify(
                description=arguments["description"],
                amount=arguments["amount"],
                is_credit=arguments.get("is_credit", True),
            )
            return json.dumps(asdict(result), default=str)

        elif tool_name == "convert_currency":
            result = currency_engine.convert_to_ngn(
                amount=arguments["amount"],
                currency=arguments["currency"],
            )
            return json.dumps(asdict(result), default=str)

        elif tool_name == "run_scenario":
            result = scenario_modeler.compare_income_change(
                current_income=arguments["current_income"],
                projected_income=arguments.get("projected_income", arguments["current_income"]),
            )
            return json.dumps(asdict(result), default=str)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
