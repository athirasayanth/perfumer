/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { formatCurrency } from '@web/core/currency';

export class CustomDialog extends Component {
  static template = "cdx_perfumer.estimation_popup_template";
  static components = { Dialog };
  static props = {
    estimationId: Number,  // Estimation ID
    orderId: Number,       // Sale Order ID (if needed)
    saleOrderLineId: Number, // Sale Order Line ID
    currentSelected:Object,
    record:Object,
    resolve: Function,     // Function to handle selection
    reject: Function,
close:Function};
  static defaultProps = {};

  setup() {
    this.state = useState({
      estimationLines: [],
      selectedLines: [],
      pselected:[],
      totalAmount:0
    });
    this.orm = useService("orm");
    this.actionService = useService("action");
    this.state = useState({
      estimationLines: [],
      selectedLines: [],
      oldselectedLines:[],
      pselected:[],
      totalAmount:0
    });

    // Load estimation lines when popup opens
    onWillStart(async () => {
      if (!this.props.estimationId) return;
      console.log("ids selceted",this.props.currentSelected)
      const estimationLinesSelected = await this.orm.searchRead(
        "sale.order.line.estimation",
        [['id','=',this.props.currentSelected]],
        ["id","estimation_line_id", "product_uom_qty", "sale_order_line_id",]
      );
      console.log("estimationLinesSelected selceted",estimationLinesSelected)
      const estimationLines = await this.orm.searchRead(
        "cdx.estimation.line",
        [["estimation_id", "=", this.props.estimationId],['display_type','=',false]],
        ["product_id", "product_uom_qty","remaining_qty","unit_sale_price","price_subtotal"]
      );

      this.state.estimationLines = estimationLines;
      
      this.state.pselected = estimationLinesSelected.map(line => line.estimation_line_id)
      this.state.oldselectedLines = estimationLinesSelected
      this.state.estimationLines = estimationLines.map(line => ({
        ...line,
        selected: this.state.pselected.includes(line.id),  // Add selected flag
        new_qty:line.remaining_qty
      }));
      console.log("state 44",this.state)
    });
    // console.log("selected",this.props.currentSelected)
    // this.state.selectedLines.add(this.props.currentSelected)
  }

  updateQuantity(lineId, event) {
    if (!this.state.selectedLines) return; // Early exit if selectedLines is not available
    console.log("state",this.state.selectedLines)
    const line = this.state.selectedLines.find(l => l.elid === lineId);  // Find the line in selectedLines
    if (line) {
      line.product_uom_qty = parseInt(event.target.value, 10) || 1;  // Update quantity
  
      // Update the estimationLines as well to reflect the change
      this.state.estimationLines = this.state.estimationLines.map(estLine =>
        estLine.id === lineId ? { ...estLine, new_qty: line.product_uom_qty } : estLine
      );
  
      console.log("Updated state after quantity change:", this.state);
      this.calculateTotal(); // Recalculate the total
    } else {
      alert("Line not found in selected lines");
    }
  }
  

  toggleSelection(lineId, event) {
    const isChecked = event.target.checked;

    // Update selectedLines immutably
    let newSelectedLines = [...this.state.selectedLines];

    if (isChecked) {
        // If checked and not already in the selected list, add it
        if (!newSelectedLines.some(line => line.elid === lineId)) {
            newSelectedLines.push({ id: lineId, elid: lineId, product_uom_qty: 0 });
        }
    } else {
        // If unchecked, remove from selectedLines
        newSelectedLines = newSelectedLines.filter(line => line.elid !== lineId);
    }

    // Update estimationLines immutably with selected flag
    const newEstimationLines = this.state.estimationLines.map(line => ({
        ...line,
        selected: newSelectedLines.some(l => l.elid === line.id) // Ensure selection flag updates
    }));

    // Assign updated values to state
    this.state.selectedLines = newSelectedLines;
    this.state.estimationLines = newEstimationLines;

    // Recalculate total price
    this.calculateTotal();
}
  

  calculateTotal() {
    this.state.totalAmount = this.state.estimationLines
        .filter(line => this.state.selectedLines.find(l => l.id ===line.id))
        .reduce((sum, line) => sum + (line.unit_sale_price * line.new_qty), 0);
}

async confirmSelection() {
  const selectedEstimationLines = this.state.estimationLines.filter(line =>
      this.state.selectedLines.find(l => l.id === line.id)
  );

  if (selectedEstimationLines.length === 0) {
      return;
  }

  const saleOrderLineId = this.props.saleOrderLineId;
  const estimationData = selectedEstimationLines.map(line => ({
      estimation_line_id: line.id,
      product_uom_qty: line.new_qty
  }));

  try {
      // Call the update_line_data method in Python (server-side)
      const response = await this.orm.call('sale.order.line', 'update_line_data', [saleOrderLineId, estimationData]);

      if (response.success) {
          console.log("Sale Order Line updated successfully:", response.message);

          // Refresh the sale order line to update price_unit in the UI
          const updatedRecord = await this.orm.read("sale.order.line", [saleOrderLineId], ["cdx_bom_id","price_unit", "cdx_estimation_line_ids"]);

          if (updatedRecord.length) {
              this.props.record.update(updatedRecord[0]); // Update UI with new values
          }
      } else {
          console.error("Error updating Sale Order Line:", response.message);
      }

      this.props.resolve(selectedEstimationLines);
      this.props.close();
  } catch (error) {
      console.error("ORM call failed:", error);
  }
}
get Total_price()
{
    return formatCurrency(this.state.totalAmount, this.props.record.data.currency_id[0]);
}
}
