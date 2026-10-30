import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig(() => {
  const INPUT_DIR = "./src_frontend";
  const OUTPUT_DIR = "./dist/";

  return {
    plugins: [react()],
    root: resolve(INPUT_DIR),
    base: "/static/",
    build: {
      sourcemap: true,
      manifest: "manifest.json",
      emptyOutDir: true,
      outDir: resolve(OUTPUT_DIR),
      rollupOptions: {
        input: {
          member_profile: resolve(
            INPUT_DIR,
            "member_profile/member_profile_entry.tsx",
          ),
          csv_export_editor: resolve(
            INPUT_DIR,
            "csv_export_editor/csv_export_editor_entry.tsx",
          ),
          pdf_export_editor: resolve(
            INPUT_DIR,
            "pdf_export_editor/pdf_export_editor_entry.tsx",
          ),
          product_config: resolve(
            INPUT_DIR,
            "product_config/product_config_entry.tsx",
          ),
          pickup_location_config: resolve(
            INPUT_DIR,
            "pickup_location_config/pickup_location_config_entry.tsx",
          ),
          contract_updates: resolve(
            INPUT_DIR,
            "contract_updates/contract_updates_entry.tsx",
          ),
          dashboard: resolve(INPUT_DIR, "dashboard/dashboard_entry.tsx"),
          waiting_list: resolve(
            INPUT_DIR,
            "waiting_list/waiting_list_entry.tsx",
          ),
          member_list: resolve(INPUT_DIR, "member_list/member_list_entry.tsx"),
          bestell_wizard_mobile: resolve(
            INPUT_DIR,
            "bestell_wizard_mobile/bestell_wizard_mobile_entry.tsx",
          ),
          bestell_wizard_coop_shares: resolve(
            INPUT_DIR,
            "member_profile/coop_shares/bestell_wizard_coop_shares.tsx",
          ),
          bestell_wizard_product_type: resolve(
            INPUT_DIR,
            "member_profile/subscriptions/bestell_wizard_product_type.tsx",
          ),
          waiting_list_confirm: resolve(
            INPUT_DIR,
            "waiting_list/waiting_list_confirm_entry.tsx",
          ),
          subscription_list: resolve(
            INPUT_DIR,
            "subscription_list/subscription_list_entry.tsx",
          ),
          credit_list: resolve(INPUT_DIR, "credit_list/credit_list_entry.tsx"),
          configuration: resolve(
            INPUT_DIR,
            "configuration/configuration_entry.tsx",
          ),
          payment_transactions: resolve(
            INPUT_DIR,
            "payment_transactions/payment_transactions_list_view_entry.tsx",
          ),
          association_memberships_config: resolve(
            INPUT_DIR,
            "association_memberships_config/association_memberships_config_entry.tsx",
          ),
          bestell_wizard_association_membership: resolve(
            INPUT_DIR,
            "member_profile/association_membership/bestell_wizard_association_membership.tsx",
          ),
          mailing_lists: resolve(
            INPUT_DIR,
            "mailing_lists/mailing_lists_entry.tsx",
          ),
          choose_breads: resolve(
            INPUT_DIR,
            "bakery/entries/choose_breads_entry.tsx",
          ),
          reports: resolve(INPUT_DIR, "bakery/entries/reports_entry.tsx"),
          ingredients_labels_breads: resolve(
            INPUT_DIR,
            "bakery/entries/ingredients_labels_breads_entry.tsx",
          ),
          weekly_plan_breads: resolve(
            INPUT_DIR,
            "bakery/entries/weekly_plan_breads_entry.tsx",
          ),
          bidding_round: resolve(
            INPUT_DIR,
            "bidding_round/bidding_round_entry.tsx",
          ),
          bidding_round_config: resolve(
            INPUT_DIR,
            "bidding_round_config/bidding_round_config_entry.tsx",
          ),
          bidding_round_results: resolve(
            INPUT_DIR,
            "bidding_round_results/bidding_round_results_entry.tsx",
          ),
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      cors: true,
    },
  };
});
