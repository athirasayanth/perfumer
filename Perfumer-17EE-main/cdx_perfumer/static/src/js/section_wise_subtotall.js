/** @odoo-module **/
import {SectionAndNoteListRenderer } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend"
import { patch } from "@web/core/utils/patch";

patch(SectionAndNoteListRenderer.prototype,{
    /*** The purpose of this patch is to allow sections in the one2many list
      primarily used on Sales Orders, Purchase Order and Invoices*/
    setup(){
    /** This function help to access the subtotal field in order line*/
        super.setup();
        this['subtotal_titleField'] = "price_subtotal"
        this['subtotal_quantityField'] = "product_uom_qty"; // New field for quantity total

    },
    isSectionOrNote(record = null) {
        /*Function to calculate the subtotal in a section */
        if(this.record){
            if (this.record.data['display_type'] === 'line_section') {
                var sequence = this.record.data.sequence;
                var all_rows = this.list.records;
                var subtotal = 0.0;
                var total_qty = 0.0;
                var self_found = false;
                for (var i = 0; i < all_rows.length; i++) {
                    var row = all_rows[i].data;
                    // If the current section's sequence matches, start calculating subtotal
                    if (row.sequence == sequence) {
                        self_found = true;
                        continue;
                    }
                    // Stop accumulating subtotal when another section is found
                    if (self_found) {
                        if (row.display_type === 'line_section' && row.sequence != sequence){
                            break;
                        }
                        // Ensure that we are only adding product lines (not sections or notes)
                        if (!['line_section', 'line_note'].includes(row.display_type)) {
                            subtotal += row.price_subtotal || 0; // Add only product subtotals
                            total_qty += row.product_uom_qty || 0; // Add only product quantities

                        }
                    }
                }
                // Assign the calculated subtotal to the section's price_subtotal field
                this.record.data.price_subtotal = subtotal;
                this.record.data.product_uom_qty = total_qty; // Store total quantity

            }
        }
        console.log("record",record)
        console.log("this record",this.record)
        record = record;
        return ['line_section', 'line_note'].includes(record.data.display_type);
    },
    getCellClass(column, record) {
        /*Help to hide the fields in order line except Description and Subtotal*/
        var classNames = super.getCellClass(column, record);
        // const element = document.querySelector(".o_field_x2many_list"); // Adjust selector based on your table
        setTimeout(() => {
            const element = document.querySelector(".o_list_view");
            if (element instanceof Element) {
                try {
                    const styles = window.getComputedStyle(element);
                    console.log("Element Styles:", styles);
                } catch (error) {
                    console.warn("Error getting computed style:", error);
                }
            } else {
                console.warn("Element not found for getComputedStyle!");
            }
        }, 500); 
        if (this.isSectionOrNote(record) && column.widget !== "handle" && column.name !== this.titleField && column.name !== this.subtotal_titleField && column.name !== this.subtotal_quantityField) {
            return `${classNames} o_hidden`;
        }
        if (column.name == 'price_subtotal' && classNames.includes("o_hidden")){
            classNames = classNames.replace("o_hidden", "").trim();
        }
        return classNames;
    },
    getColumns(record) {
        /*Check whether we select Line section or Line note and call
         the corresponding function*/
        const columns = this.columns;
        if (this.isSectionOrNote(record)) {
            if(record.data.display_type == 'line_note'){
                const columns = this.columns;
                return this.getSectionColumns(columns);
            }
            else{
                const columns = this.columns;
                return this.getSubtotalSectionColumns(columns);
            }
        }
        return columns;
    },
    // getSubtotalSectionColumns(columns) {
    //     /* Ensure that the subtotal field is visible in the section rows */
    //     console.log("model", this.record.resModel);
    //     const sectionCols = columns.filter((col) => col.widget === "handle" || col.type === "field" && col.name === this.subtotal_titleField || col.type === "field" && col.name === this.titleField || col.type =='field' && col.name === this.subtotal_quantityField);
    //     // const sectionCols = columns.filter((col) =>
    //     //     col.widget === "handle" || 
    //     //     (col.type === "field" && 
    //     //     (col.name === this.titleField || 
    //     //      col.name === this.subtotal_quantityField || 
    //     //      col.name === this.subtotal_titleField ))
    //     // );

    //     var firstcolspan=1;
    //     console.log("columns",columns)
    //     var lastcolspan = columns.length - sectionCols.length + 1;
    //     if (this.record.resModel == 'cdx.estimation.line')
    //     {
    //         firstcolspan = 2;
    //         // lastcolspan =21;
    //     }

    //     return columns.map((col) => {
    //         if (col.name === this.titleField) {
    //             console.log("total a");
    //             return { ...col, colspan: columns.length - sectionCols.length + 1  };
    //         }
    //         // if (col.name === this.subtotal_quantityField) {
    //         //     console.log("total b");
    //         //     return { ...col }; // Ensure these columns are aligned properly
    //         // }
    //         // console.log("col",col)
    //         // if(col.name === this.subtotal_titleField)
    //         // {
    //         //     return { ...col, colspan: lastcolspan };
    //         // }
    //         // else if(col.name === 'total_cost' && col.string==="Total Cost")
    //         //     {
    //         //         return { ...col, colspan: 7 };
    //         //     }
    //         else {
    //             return { ...col };
    //         }
    //         // return col;
    //     });
    // }

    getSubtotalSectionColumns(columns) {
        /* Ensure that the subtotal and quantity fields are visible in section rows */
        console.log("model", this.record.resModel);
    
        // Filter the required columns: Handle, Title, Quantity, and Subtotal
        const sectionCols = columns.filter((col) => 
            col.widget === "handle" || 
            (col.type === "field" && 
            (col.name === this.titleField || 
             col.name === this.subtotal_quantityField || 
             col.name === this.subtotal_titleField))
        );
    
        var firstColspan = 1;
        var lastColspan = columns.length - sectionCols.length + 1;
    
        // Adjust colspan if the model is 'cdx.estimation.line'
        if (this.record.resModel == 'cdx.estimation.line') {
            firstColspan = 2;
        }
    
        return columns.map((col) => {
            if (col.name === this.titleField) {
                console.log("total a");
                return { ...col, colspan: firstColspan };
            }
            if (col.name === this.subtotal_quantityField || col.name === this.subtotal_titleField) {
                console.log("total b");
                return { ...col, colspan: lastColspan };
            }
            return { ...col };
        });
    }
});
