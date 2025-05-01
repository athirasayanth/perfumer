/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart,EventBus } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

class StockAvailabilityWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.bus = new EventBus();
        this.closePopover = null;
        this.state = useState({
            stockData: [],
            totalQty: 0,
        });
        const position = "top";
        this.popover = usePopover(this.constructor.components.Popover, { position });
        // Load stock data
        onWillStart(async () => {
            await this.loadStockData();
        });
    }

    async loadStockData() {
        if (!this.props.record.data.product_id) {
            return;
        }
        const productId = this.props.record.data.product_id[0];

        const result = await this.orm.call(
            "material.request",
            "get_stock_availability",
            [productId]
        );

        this.state.stockData = result.stock_details;
        this.state.totalQty = result.total_qty;
    }

    showPopup(ev) {
        this.closePopover = this.popover.open(ev.currentTarget, { stockData: this.state.stockData, totalQty: this.state.totalQty,});
        this.bus.addEventListener('close-popover', this.closePopover);
    }
}

// Define the Pop-up Component
class StockAvailabilityPopup extends Component {}

StockAvailabilityWidget.template = "cdx_iec_material_req.StockAvailabilityWidget";
StockAvailabilityWidget.components = { Popover: StockAvailabilityPopup }

StockAvailabilityPopup.template = "cdx_iec_material_req.StockAvailabilityPopup";

// Register the widget in the field registry
registry.category("fields").add("stock_availability_widget", {
    component: StockAvailabilityWidget,
});
