from Products.ERP5Type.Message import translateString

request = context.REQUEST

item_portal_type = kw.get('type')

item_property_dict = {}

# if the formbox for extra item properties is enabled, use it.
dialog = getattr(context, dialog_id)
if dialog.has_field('your_item_extra_property_list'):
  box = dialog.get_field('your_item_extra_property_list')
  form = getattr(context, box.get_value('formbox_target_id'))
  for field in form.get_fields():
    field_id = field.getId()
    if field_id.startswith('your_'):
      item_property_dict[field_id.replace('your_', '', 1)] =\
                                    request.get(field_id)

movement_cell_list = context.getCellValueList()
base_id = 'movement'

for line in kw.get('listbox'):

  if line.has_key('listbox_key'):
    item_reference = line.get('reference')
    item = None
    if item_reference:
      item = context.portal_catalog.getResultValue(
                                      portal_type=item_portal_type,
                                      reference=item_reference)
    if item is None:
      module = context.getDefaultModule(item_portal_type)
      item = module.newContent(portal_type=item_portal_type,
                               title=line['title'],
                               reference=item_reference,
                               quantity=line.get('quantity'),
                               quantity_unit=context.getQuantityUnit(),
                               **item_property_dict)

    line_variation_category_list = []
    for variation in (
          line.get('line_variation_category_list'),
          line.get('column_variation_category_list'),
          line.get('tab_variation_category_list'),):
      if variation:
        line_variation_category_list.append(variation)


    if line_variation_category_list:
      cell_found = context.getCell(base_id='movement',
                                   *line_variation_category_list)
      if cell_found is not None:
        movement_to_update = cell_found
      else:
        if not context.hasInRange(base_id='movement',
                                  *line_variation_category_list):
          # update line variation category list, if not already containing this one
          variation_category_list = context.getVariationCategoryList()
          for variation in line_variation_category_list:
            if variation not in variation_category_list:
              variation_category_list.append(variation)
          context.setVariationCategoryList(variation_category_list)
        movement_to_update = context.newCell(base_id='movement',
                                             *line_variation_category_list)
        movement_to_update.edit(mapped_value_property_list=('quantity', 'price'),
                                variation_category_list=line_variation_category_list)
 
    else:
      # no variation, we'll update the line itself
      movement_to_update = context

    if item.getRelativeUrl() not in movement_to_update.getAggregateList():
      movement_to_update.setAggregateValueList(
        movement_to_update.getAggregateValueList() + [item])

return context.Base_redirect(form_id, keep_items=dict(
      portal_status_message=translateString('Items created')))
