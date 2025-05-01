/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";
import { CustomDialog } from "./dialog.js";

export class My_Custom extends Component {
  static props = { ...standardFieldProps };
  static template = "cdx_perfumer.bom";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.dialogService = useService("dialog");
  }

  onInfoClick(ev) {
    this.openEstimationPopup();
  }

  // Method to open the popup dialog
  openEstimationPopup() {

    this.dialogService.add(CustomDialog, {
      estimationId: this.props.record.data.cdx_estimation_id[0],
      currentSelected:this.props.record.data.cdx_estimation_line_ids._currentIds,
      orderId: this.props.record.evalContext.active_id,
      saleOrderLineId: this.props.record.data.id,
      record:this.props.record,
      resolve: (estimationLines) => {
        console.log("Selected Estimation Lines:", estimationLines);
        //     // TODO: Add logic to update sale order lines with selected estimation lines
      },
      reject: () => console.log("Popup closed"),
    });
  }
}

export const my_custom = {
  component: My_Custom,
  supportedTypes: ["char"],
};

registry.category("fields").add("estimation_popup_button", my_custom);
