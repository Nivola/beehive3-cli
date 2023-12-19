# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class AuthorityControllerChild(BusinessControllerChild):
    def _format_report_cost_response(self, response):
        if self.format == "text":
            self.app.render(
                response,
                maxsize=160,
                headers=[
                    "organization",
                    "division",
                    "account",
                    "hasvat",
                    "amount",
                    "start_date",
                    "end_date",
                    "referent",
                    "email",
                    "postal_address",
                ],
                fields=[
                    "organization",
                    "division",
                    "account",
                    "hasvat",
                    "amount",
                    "period.start_date",
                    "period.end_date",
                    "referent",
                    "email",
                    "postal_address",
                ],
            )

            self.app.print_output("Credit composition - Agreements:")
            agreements = response.get("credit_composition", {}).get("agreements", [])
            self.app.render(
                agreements,
                maxsize=200,
                table_style="simple",
                headers=[
                    "agreement_id",
                    "agreement",
                    "date_start",
                    "amount",
                    "date_end",
                    "amount",
                ],
                fields=[
                    "agreement_id",
                    "agreement",
                    "date_start",
                    "amount",
                    "date_end",
                    "amount",
                ],
            )

            self.app.print_output("Credit summary:")
            cs = response.get("credit_summary", {})
            self.app.render(
                cs,
                maxsize=200,
                table_style="simple",
                headers=[
                    "initial",
                    "accounted",
                    "remaining_pre",
                    "consume_period",
                    "remaining_post",
                ],
                fields=[
                    "initial",
                    "accounted",
                    "remaining_pre",
                    "consume_period",
                    "remaining_post",
                ],
            )

            self.app.print_output("Services:")
            services = response.get("services", [])
            self.app.render(
                services,
                headers=["total", "name", "plugin_name", "details", "summary_consume"],
                fields=["total", "name", "plugin_name", "details", "summary_consume"],
                maxsize=200,
                table_style="simple",
            )
        else:
            self.app.render(response)
