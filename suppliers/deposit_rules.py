from decimal import Decimal


DEPOSIT_AMOUNTS_PLN = {
    "01": {
        **{code: Decimal("500.00") for code in (
            "MCMR", "EDMR", "EDAR", "CDMR", "CLMR", "CDAR", "CLAR",
            "CLAH", "CWMR", "CWAR", "DLAR", "SWAR", "IFMR", "IFAR",
            "FFMR", "FFAR", "SPAR", "FVMR", "FVAR", "CVMR", "CKMR",
            "OKMR", "SVAR", "FCAH",
        )},
        **{code: Decimal("1000.00") for code in (
            "PLAR", "PFAR", "PFAH", "LFAR",
        )},
    },
    "02": {
        **{code: Decimal("500.00") for code in (
            "EDMR", "CDMR", "CDAR", "CWAR", "SWAR", "SLAR", "IGAH",
            "IGMR", "IFAR", "FFAR", "FVAR", "SVAD", "PVMD", "PVAD",
            "SKMD",
        )},
        **{code: Decimal("2000.00") for code in (
            "RLAR", "PLAH", "RGAR", "PFBD", "LFBD",
        )},
    },
    "03": {
        **{code: Decimal("500.00") for code in (
            "B-MANUAL", "B-AUTOMATIC", "C-CROSSOVER-AUTOMATIC",
            "C-STATION-WAGON-AUTOMATIC", "D-AUTOMATIC",
            "D-PREMIUM-AUTOMATIC", "SUV-BIG-AUTOMATIC",
            "SUV-MEDIUM-AUTOMATIC",
        )},
        **{code: Decimal("1500.00") for code in (
            "SUV-7-SEATER-AUTOMATIC", "E-AUTOMATIC",
            "SUV-MEDIUM-PREMIUM-AUTOMATIC", "BUS-9-SEATER-AUTOMATIC",
        )},
    },
}


def default_deposit_amount(supplier_code, group_code):
    return DEPOSIT_AMOUNTS_PLN.get(supplier_code, {}).get(group_code)
