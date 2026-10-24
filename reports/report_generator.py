import math
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportGenerator:

    def __init__(self):
        self.styles = getSampleStyleSheet()

        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Heading1"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            spaceAfter=8,
        )

        self.subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=self.styles["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.grey,
            spaceAfter=10,
        )

        self.heading_style = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.darkblue,
            spaceBefore=8,
            spaceAfter=8,
        )

        self.normal = ParagraphStyle(
            "ReportBody",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
        )

        self.small = ParagraphStyle(
            "SmallText",
            parent=self.normal,
            fontSize=8,
            leading=10,
            textColor=colors.grey,
        )

    # ======================================================
    # FORMATTERS
    # ======================================================

    @staticmethod
    def _safe_float(value):
        try:
            number = float(value)
            if math.isnan(number) or math.isinf(number):
                return None
            return number
        except (TypeError, ValueError):
            return None

    def _format_number(self, value, decimals=2):
        number = self._safe_float(value)
        if number is None:
            return "N/A"
        return f"{number:,.{decimals}f}"

    def _format_price(self, value):
        number = self._safe_float(value)
        if number is None:
            return "N/A"
        return f"Rs. {number:,.2f}"

    def _format_percent(self, value):
        number = self._safe_float(value)
        if number is None:
            return "N/A"
        return f"{number * 100:.2f}%"

    def _format_dividend_yield(self, value):
        if value in [None, "N/A"]:
            return "N/A"
        try:
            return f"{float(value):.2f}%"
        except (TypeError, ValueError):
            return str(value)

    def _format_market_cap(self, value):
        number = self._safe_float(value)
        if number is None:
            return "N/A"

        if number >= 1e12:
            return f"Rs. {number / 1e12:.2f} Lakh Cr"
        if number >= 1e7:
            return f"Rs. {number / 1e7:,.2f} Cr"
        if number >= 1e5:
            return f"Rs. {number / 1e5:,.2f} Lakh"

        return f"Rs. {number:,.0f}"

    # ======================================================
    # PDF HELPERS
    # ======================================================

    def _section_title(self, title):
        return Paragraph(title, self.heading_style)

    def _bullet(self, text):
        return Paragraph(f"&#8226; {text}", self.normal)

    def _table(self, rows):
        formatted_rows = []

        for row_index, row in enumerate(rows):
            formatted_row = []
            for cell in row:
                style = self.small if row_index == 0 else self.normal
                formatted_row.append(
                    Paragraph(
                        str(cell),
                        style,
                    )
                )
            formatted_rows.append(formatted_row)

        table = Table(
            formatted_rows,
            colWidths=[
                2.4 * inch,
                3.6 * inch,
            ],
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.darkblue,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.lightgrey,
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        colors.whitesmoke,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        return table

    # ======================================================
    # HEADER / FOOTER
    # ======================================================

    def _draw_header_footer(self, canvas, doc):
        canvas.saveState()

        width, height = A4

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.darkblue)
        canvas.drawString(
            doc.leftMargin,
            height - 28,
            "AI STOCK ANALYZER PRO",
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            width - doc.rightMargin,
            height - 28,
            "Equity Research Report",
        )

        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(
            doc.leftMargin,
            height - 34,
            width - doc.rightMargin,
            height - 34,
        )
        canvas.line(
            doc.leftMargin,
            32,
            width - doc.rightMargin,
            32,
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            doc.leftMargin,
            20,
            "AI Stock Analyzer Pro",
        )
        canvas.drawRightString(
            width - doc.rightMargin,
            20,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # ======================================================
    # GENERATE REPORT
    # ======================================================

    def generate(
        self,
        symbol,
        data,
        investment_score,
        technical_score,
        fundamental_score,
        recommendation,
        technical_reasons,
        fundamental_reasons,
        news,
        trade_plan=None,
        score_breakdown=None,
        ai_result=None,
        valuation_analysis=None,
    ):
        output_folder = Path("generated_reports")
        output_folder.mkdir(parents=True, exist_ok=True)

        safe_symbol = str(symbol).strip().upper().replace("/", "_").replace("\\", "_")
        pdf_path = output_folder / f"{safe_symbol}_Research_Report.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=0.55 * inch,
            leftMargin=0.55 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.55 * inch,
            title=f"{safe_symbol} Equity Research Report",
            author="AI Stock Analyzer Pro",
        )

        story = []
        company = data.get("company", safe_symbol)
        generated = datetime.now()

        # ==================================================
        # CLEAN PDF RECOMMENDATION
        # ==================================================

        pdf_recommendation = str(recommendation or "N/A").strip()

        score_breakdown = score_breakdown or {}
        ai_result = ai_result or {}
        valuation_analysis = valuation_analysis or {}

        ai_score = self._safe_float(score_breakdown.get("AI", ai_result.get("score")))
        stability_score = self._safe_float(score_breakdown.get("Stability"))
        technical_contribution = self._safe_float(score_breakdown.get("Technical Contribution"))
        fundamental_contribution = self._safe_float(score_breakdown.get("Fundamental Contribution"))
        ai_contribution = self._safe_float(score_breakdown.get("AI Contribution"))
        stability_contribution = self._safe_float(score_breakdown.get("Stability Contribution"))

        contribution_values = [
            technical_contribution,
            fundamental_contribution,
            ai_contribution,
            stability_contribution,
        ]
        weighted_total = (
            sum(value for value in contribution_values if value is not None)
            if any(value is not None for value in contribution_values)
            else None
        )

        stability_reasons = score_breakdown.get("Stability Reasons", [])
        if not isinstance(stability_reasons, (list, tuple)):
            stability_reasons = []

        # ==================================================
        # REPORT TITLE
        # ==================================================

        story.append(Spacer(1, 0.25 * inch))
        story.append(
            Paragraph(
                "AI STOCK ANALYZER PRO",
                self.title_style,
            )
        )
        story.append(
            Paragraph(
                "Professional Equity Research Report",
                self.subtitle_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>{company}</b>",
                self.title_style,
            )
        )
        story.append(
            Paragraph(
                f"NSE Symbol: {safe_symbol}",
                self.subtitle_style,
            )
        )
        story.append(
            Paragraph(
                generated.strftime("%d %B %Y, %H:%M"),
                self.subtitle_style,
            )
        )

        # ==================================================
        # EXECUTIVE SUMMARY
        # ==================================================

        story.append(self._section_title("Executive Summary"))
        story.append(
            self._table(
                [
                    ["Metric", "Result"],
                    ["Investment Score V2", f"{investment_score}/100"],
                    ["Technical Score", f"{technical_score}/100"],
                    ["Fundamental Score", f"{fundamental_score}/100"],
                    [
                        "AI Model Score",
                        f"{ai_score:.0f}/100" if ai_score is not None else "N/A",
                    ],
                    [
                        "Stability Score",
                        (f"{stability_score:.0f}/100" if stability_score is not None else "N/A"),
                    ],
                    ["Recommendation", pdf_recommendation],
                ]
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # INVESTMENT SCORE V2 BREAKDOWN
        # ==================================================

        story.append(self._section_title("Investment Score V2 Breakdown"))
        story.append(
            self._table(
                [
                    ["Component", "Score / Weighted Contribution"],
                    [
                        "Technical (35%)",
                        (
                            f"{technical_score}/100 | {technical_contribution:.2f}/35"
                            if technical_contribution is not None
                            else f"{technical_score}/100"
                        ),
                    ],
                    [
                        "Fundamental (40%)",
                        (
                            f"{fundamental_score}/100 | {fundamental_contribution:.2f}/40"
                            if fundamental_contribution is not None
                            else f"{fundamental_score}/100"
                        ),
                    ],
                    [
                        "AI Model (15%)",
                        (
                            f"{ai_score:.0f}/100 | {ai_contribution:.2f}/15"
                            if ai_score is not None and ai_contribution is not None
                            else (f"{ai_score:.0f}/100" if ai_score is not None else "N/A")
                        ),
                    ],
                    [
                        "Stability (10%)",
                        (
                            f"{stability_score:.0f}/100 | {stability_contribution:.2f}/10"
                            if stability_score is not None and stability_contribution is not None
                            else (
                                f"{stability_score:.0f}/100"
                                if stability_score is not None
                                else "N/A"
                            )
                        ),
                    ],
                    [
                        "Weighted Total",
                        (
                            f"{weighted_total:.2f}/100 -> {investment_score}/100"
                            if weighted_total is not None
                            else f"{investment_score}/100"
                        ),
                    ],
                ]
            )
        )

        if stability_reasons:
            story.append(Spacer(1, 0.10 * inch))
            story.append(self._section_title("Stability Assessment"))
            for reason in stability_reasons:
                story.append(self._bullet(reason))
                story.append(Spacer(1, 0.04 * inch))

        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # TARGET PRICE & TRADE PLANNING
        # ==================================================

        if trade_plan and trade_plan.get("status") == "OK":
            risk_reward = self._safe_float(trade_plan.get("risk_reward"))

            risk_reward_text = f"1 : {risk_reward:.2f}" if risk_reward is not None else "N/A"

            upside = self._safe_float(trade_plan.get("upside_percent"))

            upside_text = f"{upside:.2f}%" if upside is not None else "N/A"

            support = trade_plan.get("support")
            resistance = trade_plan.get("resistance")
            trade_signal = trade_plan.get(
                "signal",
                "N/A",
            )
            setup_quality = trade_plan.get(
                "setup_quality",
                "N/A",
            )
            trade_note = trade_plan.get(
                "trade_note",
                "",
            )

            trade_plan_table = self._table(
                [
                    ["Metric", "Value"],
                    [
                        "Current Price",
                        self._format_price(trade_plan.get("current_price")),
                    ],
                    [
                        "Target Price",
                        self._format_price(trade_plan.get("target_price")),
                    ],
                    [
                        "Potential Upside",
                        upside_text,
                    ],
                    [
                        "Stop Loss",
                        self._format_price(trade_plan.get("stop_loss")),
                    ],
                    [
                        "Risk / Reward",
                        risk_reward_text,
                    ],
                    [
                        "ATR",
                        self._format_price(trade_plan.get("atr")),
                    ],
                    [
                        "Support",
                        self._format_price(support),
                    ],
                    [
                        "Resistance",
                        self._format_price(resistance),
                    ],
                    [
                        "Trade Signal",
                        trade_signal,
                    ],
                    [
                        "Setup Quality",
                        setup_quality,
                    ],
                ]
            )

            # Keep heading and table on the same page.
            story.append(
                KeepTogether(
                    [
                        self._section_title("Target Price & Trade Planning"),
                        trade_plan_table,
                    ]
                )
            )

            story.append(Spacer(1, 0.10 * inch))

            if trade_note:
                story.append(
                    Paragraph(
                        f"<b>Trade Plan Note:</b> {trade_note}",
                        self.normal,
                    )
                )

                story.append(Spacer(1, 0.08 * inch))

            story.append(
                Paragraph(
                    (
                        "Target price, stop-loss, support and "
                        "resistance levels are rule-based estimates "
                        "derived from historical price data, "
                        "volatility, market structure and technical "
                        "conditions."
                    ),
                    self.small,
                )
            )

        else:
            story.append(
                KeepTogether(
                    [
                        self._section_title("Target Price & Trade Planning"),
                        Paragraph(
                            "Trade planning data is unavailable.",
                            self.normal,
                        ),
                    ]
                )
            )

        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # COMPANY PROFILE
        # ==================================================

        company_profile_block = [
            self._section_title("Company Profile"),
            self._table(
                [
                    [
                        "Field",
                        "Value",
                    ],
                    [
                        "Company",
                        company,
                    ],
                    [
                        "Sector",
                        data.get(
                            "sector",
                            "N/A",
                        ),
                    ],
                    [
                        "Industry",
                        data.get(
                            "industry",
                            "N/A",
                        ),
                    ],
                    [
                        "Current Price",
                        self._format_price(data.get("price")),
                    ],
                    [
                        "Market Cap",
                        self._format_market_cap(data.get("market_cap")),
                    ],
                    [
                        "Currency",
                        data.get(
                            "currency",
                            "N/A",
                        ),
                    ],
                ]
            ),
        ]

        story.append(KeepTogether(company_profile_block))
        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # FINANCIAL ANALYSIS
        # ==================================================

        financial_analysis_block = [
            self._section_title("Financial Analysis"),
            self._table(
                [
                    [
                        "Metric",
                        "Value",
                    ],
                    [
                        "P/E Ratio",
                        self._format_number(data.get("pe")),
                    ],
                    [
                        "P/B Ratio",
                        self._format_number(data.get("pb")),
                    ],
                    [
                        "EPS",
                        self._format_price(data.get("eps")),
                    ],
                    [
                        "Beta",
                        self._format_number(data.get("beta")),
                    ],
                    [
                        "ROE",
                        self._format_percent(data.get("roe")),
                    ],
                    [
                        "Profit Margin",
                        self._format_percent(data.get("profit_margin")),
                    ],
                    [
                        "Operating Margin",
                        self._format_percent(data.get("operating_margin")),
                    ],
                    [
                        "Dividend Yield",
                        self._format_dividend_yield(data.get("dividend_yield")),
                    ],
                    ["ROA", self._format_percent(data.get("roa"))],
                    ["Forward P/E", self._format_number(data.get("forward_pe"))],
                    [
                        "Debt / Equity",
                        (
                            f"{self._safe_float(data.get('debt_to_equity')) / 100:.2f}x"
                            if self._safe_float(data.get("debt_to_equity")) is not None
                            else "N/A"
                        ),
                    ],
                    ["Current Ratio", self._format_number(data.get("current_ratio"))],
                    [
                        "Revenue Growth",
                        self._format_percent(data.get("revenue_growth")),
                    ],
                    [
                        "Earnings Growth",
                        self._format_percent(data.get("earnings_growth")),
                    ],
                    ["Total Debt", self._format_market_cap(data.get("total_debt"))],
                    ["Total Cash", self._format_market_cap(data.get("total_cash"))],
                    [
                        "Operating Cash Flow",
                        self._format_market_cap(data.get("operating_cash_flow")),
                    ],
                    [
                        "Free Cash Flow",
                        self._format_market_cap(data.get("free_cash_flow")),
                    ],
                ]
            ),
        ]

        story.append(KeepTogether(financial_analysis_block))

        story.append(
            Spacer(
                1,
                0.2 * inch,
            )
        )

        # ==================================================
        # FUNDAMENTAL VALUATION V3
        # ==================================================

        story.append(self._section_title("Fundamental Valuation V3"))

        if valuation_analysis.get("status") == "OK":

            valuation_current_price = self._safe_float(valuation_analysis.get("current_price"))

            valuation_fair_value = self._safe_float(valuation_analysis.get("fair_value"))

            valuation_bear_value = self._safe_float(valuation_analysis.get("bear_value"))

            valuation_bull_value = self._safe_float(valuation_analysis.get("bull_value"))

            valuation_upside = self._safe_float(valuation_analysis.get("upside_percent"))

            valuation_margin_of_safety = self._safe_float(
                valuation_analysis.get("margin_of_safety")
            )

            valuation_trailing_pe = self._safe_float(valuation_analysis.get("trailing_pe"))

            valuation_forward_pe = self._safe_float(valuation_analysis.get("forward_pe"))

            valuation_base_pe = self._safe_float(valuation_analysis.get("base_pe"))

            valuation_fair_pe = self._safe_float(valuation_analysis.get("fair_pe"))

            valuation_status = valuation_analysis.get(
                "valuation_status",
                "N/A",
            )

            valuation_conviction = valuation_analysis.get(
                "valuation_conviction",
                "N/A",
            )

            # ==============================================
            # VALUATION SUMMARY TABLE
            # ==============================================

            story.append(
                self._table(
                    [
                        ["Metric", "Value"],
                        [
                            "Current Price",
                            self._format_price(valuation_current_price),
                        ],
                        [
                            "Estimated Fair Value",
                            self._format_price(valuation_fair_value),
                        ],
                        [
                            "Upside / Downside",
                            (
                                f"{valuation_upside:+.2f}%"
                                if valuation_upside is not None
                                else "N/A"
                            ),
                        ],
                        [
                            "Valuation Status",
                            str(valuation_status),
                        ],
                        [
                            "Valuation Conviction",
                            str(valuation_conviction),
                        ],
                        [
                            "Margin of Safety",
                            (
                                f"{valuation_margin_of_safety:.2f}%"
                                if valuation_margin_of_safety is not None
                                else "N/A"
                            ),
                        ],
                    ]
                )
            )

            story.append(
                Spacer(
                    1,
                    0.12 * inch,
                )
            )

            # ==============================================
            # VALUATION RANGE
            # ==============================================

            story.append(
                Paragraph(
                    "<b>Valuation Range</b>",
                    self.normal,
                )
            )

            story.append(
                Spacer(
                    1,
                    0.06 * inch,
                )
            )

            story.append(
                self._table(
                    [
                        ["Scenario", "Estimated Value"],
                        [
                            "Bear Value",
                            self._format_price(valuation_bear_value),
                        ],
                        [
                            "Base Fair Value",
                            self._format_price(valuation_fair_value),
                        ],
                        [
                            "Bull Value",
                            self._format_price(valuation_bull_value),
                        ],
                    ]
                )
            )

            story.append(
                Spacer(
                    1,
                    0.12 * inch,
                )
            )

            # ==============================================
            # P/E VALUATION
            # ==============================================

            story.append(
                Paragraph(
                    "<b>P/E Valuation</b>",
                    self.normal,
                )
            )

            story.append(
                Spacer(
                    1,
                    0.06 * inch,
                )
            )

            story.append(
                self._table(
                    [
                        ["Metric", "Multiple"],
                        [
                            "Trailing P/E",
                            (
                                f"{valuation_trailing_pe:.2f}x"
                                if valuation_trailing_pe is not None
                                else "N/A"
                            ),
                        ],
                        [
                            "Forward P/E",
                            (
                                f"{valuation_forward_pe:.2f}x"
                                if valuation_forward_pe is not None
                                else "N/A"
                            ),
                        ],
                        [
                            "Base P/E",
                            (
                                f"{valuation_base_pe:.2f}x"
                                if valuation_base_pe is not None
                                else "N/A"
                            ),
                        ],
                        [
                            "Model Fair P/E",
                            (
                                f"{valuation_fair_pe:.2f}x"
                                if valuation_fair_pe is not None
                                else "N/A"
                            ),
                        ],
                    ]
                )
            )

            story.append(
                Spacer(
                    1,
                    0.12 * inch,
                )
            )

            # ==============================================
            # VALUATION FACTORS
            # ==============================================

            valuation_reasons = valuation_analysis.get(
                "reasons",
                [],
            )

            if (
                isinstance(
                    valuation_reasons,
                    (list, tuple),
                )
                and valuation_reasons
            ):

                story.append(
                    Paragraph(
                        "<b>Valuation Factors</b>",
                        self.normal,
                    )
                )

                story.append(
                    Spacer(
                        1,
                        0.06 * inch,
                    )
                )

                for reason in valuation_reasons:
                    story.append(self._bullet(str(reason)))

                    story.append(
                        Spacer(
                            1,
                            0.03 * inch,
                        )
                    )

            story.append(
                Spacer(
                    1,
                    0.08 * inch,
                )
            )

            story.append(
                Paragraph(
                    (
                        "Fundamental Valuation V3 is a rule-based "
                        "earnings valuation model. The estimated "
                        "fair value is independent of the technical "
                        "target price and should not be interpreted "
                        "as a guaranteed future market price."
                    ),
                    self.small,
                )
            )

        else:

            valuation_message = valuation_analysis.get(
                "message",
                "Fundamental valuation is unavailable.",
            )

            story.append(
                Paragraph(
                    str(valuation_message),
                    self.normal,
                )
            )

        story.append(
            Spacer(
                1,
                0.2 * inch,
            )
        )

        # ==================================================
        # AI MODEL ANALYSIS
        # ==================================================

        ai_recommendation = ai_result.get(
            "recommendation",
            "N/A",
        )

        ai_risk = ai_result.get(
            "risk",
            "N/A",
        )

        ai_reasons = ai_result.get(
            "reasons",
            [],
        )

        # Build the complete AI section first.
        ai_analysis_block = [
            self._section_title("AI Model Analysis"),
            self._table(
                [
                    ["Metric", "Result"],
                    [
                        "AI Score",
                        (f"{ai_score:.0f}/100" if ai_score is not None else "N/A"),
                    ],
                    [
                        "AI Verdict",
                        ai_recommendation,
                    ],
                    [
                        "Risk Level",
                        ai_risk,
                    ],
                ]
            ),
        ]

        # Add AI reasons to the same block.
        if isinstance(ai_reasons, (list, tuple)) and ai_reasons:
            ai_analysis_block.append(Spacer(1, 0.10 * inch))

            for reason in ai_reasons:
                ai_analysis_block.append(self._bullet(reason))

                ai_analysis_block.append(Spacer(1, 0.04 * inch))

        # Keep heading, table and AI reasons together.
        story.append(KeepTogether(ai_analysis_block))

        story.append(Spacer(1, 0.15 * inch))

        # ==================================================
        # TECHNICAL ANALYSIS
        # ==================================================

        story.append(self._section_title("Technical Analysis"))

        if technical_reasons:
            for reason in technical_reasons:
                story.append(self._bullet(reason))
                story.append(Spacer(1, 0.04 * inch))
        else:
            story.append(
                Paragraph(
                    "No technical reasons available.",
                    self.normal,
                )
            )

        story.append(Spacer(1, 0.15 * inch))

        # ==================================================
        # FUNDAMENTAL ANALYSIS
        # ==================================================

        if fundamental_reasons:

            # Keep the heading and first few reasons together.
            fundamental_intro = [
                self._section_title("Fundamental Analysis"),
            ]

            first_reasons = fundamental_reasons[:4]
            remaining_reasons = fundamental_reasons[4:]

            for reason in first_reasons:
                fundamental_intro.append(self._bullet(reason))
                fundamental_intro.append(Spacer(1, 0.04 * inch))

            story.append(KeepTogether(fundamental_intro))

            # Allow the middle reasons to flow naturally.
            middle_reasons = remaining_reasons[:-3]
            final_reasons = remaining_reasons[-3:]

            for reason in middle_reasons:
                story.append(self._bullet(reason))
                story.append(Spacer(1, 0.04 * inch))

            # Keep the final three reasons together so that
            # a single bullet is not orphaned on the next page.
            if final_reasons:
                final_reasons_block = []

                for reason in final_reasons:
                    final_reasons_block.append(self._bullet(reason))
                    final_reasons_block.append(Spacer(1, 0.04 * inch))

                story.append(KeepTogether(final_reasons_block))

        else:
            story.append(
                KeepTogether(
                    [
                        self._section_title("Fundamental Analysis"),
                        Paragraph(
                            "No fundamental reasons available.",
                            self.normal,
                        ),
                    ]
                )
            )

        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # LATEST COMPANY NEWS
        # ==================================================

        story.append(self._section_title("Latest Company News"))

        valid_news = []
        if news:
            for article in news:
                if not isinstance(article, dict):
                    continue

                title = article.get("title", "")
                publisher = article.get("publisher", "Unknown")

                if not title:
                    continue

                valid_news.append((title, publisher))

                if len(valid_news) >= 5:
                    break

        if valid_news:
            for title, publisher in valid_news:
                story.append(
                    Paragraph(
                        f"<b>{title}</b>",
                        self.normal,
                    )
                )
                story.append(
                    Paragraph(
                        f"Source: {publisher}",
                        self.small,
                    )
                )
                story.append(Spacer(1, 0.12 * inch))
        else:
            story.append(
                Paragraph(
                    "No recent company news available.",
                    self.normal,
                )
            )

        story.append(Spacer(1, 0.2 * inch))

        # ==================================================
        # DISCLAIMER
        # ==================================================

        story.append(self._section_title("Important Disclaimer"))
        story.append(
            Paragraph(
                (
                    "This report is generated for research and educational purposes. "
                    "Investment scores, recommendations, target prices and stop-loss "
                    "levels are generated using rule-based analytical models, financial "
                    "information and historical market data. They are not guarantees of "
                    "future performance and should not be treated as personalized "
                    "investment advice."
                ),
                self.normal,
            )
        )
        story.append(Spacer(1, 0.15 * inch))
        story.append(
            Paragraph(
                f"Report generated on {generated.strftime('%d %B %Y at %H:%M')}.",
                self.small,
            )
        )

        # ==================================================
        # BUILD PDF
        # ==================================================

        doc.build(
            story,
            onFirstPage=self._draw_header_footer,
            onLaterPages=self._draw_header_footer,
        )

        return pdf_path
