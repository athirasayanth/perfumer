/** @odoo-module **/
import { SectionAndNoteListRenderer } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend"
import { patch } from "@web/core/utils/patch";

patch(SectionAndNoteListRenderer.prototype, {
    setup() {
        /** This function helps to access the subtotal and quantity fields in order lines */
        super.setup();
        this['subtotal_titleField'] = "price_subtotal";
        this['subtotal_quantityField'] = "product_uom_qty"; // New field for quantity total

    },

    isSectionOrNote(record = null) {
        /** Function to calculate the subtotal and total quantity in a section */
        if (this.record) {
            if (this.record.data['display_type'] === 'line_section') {
                var sequence = this.record.data.sequence;
                var all_rows = this.list.records;
                var subtotal = 0.0;
                var total_cost = 0.0;
                var total_qty = 0.0;
                var self_found = false;

                for (var i = 0; i < all_rows.length; i++) {
                    var row = all_rows[i].data;
                    // If the current section's sequence matches, start calculating subtotal and total qty
                    if (row.sequence == sequence) {
                        self_found = true;
                        continue;
                    }
                    // Stop accumulating subtotal and quantity when another section is found
                    if (self_found) {
                        if (row.display_type === 'line_section' && row.sequence != sequence) {
                            break;
                        }
                        // Ensure that we are only adding product lines (not sections or notes)
                        if (!['line_section', 'line_note'].includes(row.display_type)) {
                            subtotal += row.price_subtotal || 0; // Add only product subtotals
                            total_qty += row.product_uom_qty || 0; // Add only product quantities
                            // total_cost += row.total_cost  || 0;
                        }
                    }
                }
                // Assign the calculated subtotal and total quantity to the section row
                this.record.data.price_subtotal = subtotal;
                this.record.data.product_uom_qty = total_qty; // Store total quantity
                // this.record.data.total_cost = total_cost;
            }
        }
        record = record || this.record;
        return ['line_section', 'line_note'].includes(record.data.display_type);
    },

    getCellClass(column, record) {
        /** Helps to hide the fields in order line except Description, Quantity, and Subtotal */
        var classNames = super.getCellClass(column, record);
        if (this.isSectionOrNote(record) && column.widget !== "handle" && 
            column.name !== this.titleField && 
            column.name !== this.subtotal_titleField &&
            column.name !== this.subtotal_quantityField  && (column.name !== 'total_cost' && column.string==="Total Cost")) {  // Show quantity column
            return `${classNames} o_hidden`;
        }
        if ((column.name == 'price_subtotal' || column.name == 'product_uom_qty' || (column.name == 'total_cost' && column.string==="Total Cost" )) && classNames.includes("o_hidden")) {
            classNames = classNames.replace("o_hidden", "").trim();
        }
        return classNames;
    },

    getColumns(record) {
        /** Check whether we select Line section or Line note and call the corresponding function */
        const columns = this.columns;
        if (this.isSectionOrNote(record)) {
            if (record.data.display_type == 'line_note') {
                return this.getSectionColumns(columns);
            } else {
                return this.getSubtotalSectionColumns(columns);
            }
        }
        return columns;
    },

    getSubtotalSectionColumns(columns) {
        /** Ensure that the subtotal and quantity fields are visible in section rows */
        console.log("model", this.record.resModel);
        const sectionCols = columns.filter((col) =>
            col.widget === "handle" || 
            (col.type === "field" && 
            (col.name === this.titleField || 
             col.name === this.subtotal_quantityField || 
             col.name === this.subtotal_titleField || (col.name === 'total_cost' && col.string==="Total Cost")))
        );

        var firstcolspan=1;
        var lastcolspan = columns.length - sectionCols.length + 1;
        if (this.record.resModel == 'cdx.estimation.line')
        {
            firstcolspan = 2;
            lastcolspan =21;
        }

        return columns.map((col) => {
            if (col.name === this.titleField) {
                console.log("total a");
                return { ...col, colspan: firstcolspan  };
            }
            if (col.name === this.subtotal_quantityField) {
                console.log("total b");
                return { ...col }; // Ensure these columns are aligned properly
            }
            else if(col.name === this.subtotal_titleField)
            {
                return { ...col, colspan: lastcolspan };
            }
            // else if(col.name === 'total_cost' && col.string==="Total Cost")
            //     {
            //         return { ...col, colspan: 7 };
            //     }
            return col;
        });
    }
});
