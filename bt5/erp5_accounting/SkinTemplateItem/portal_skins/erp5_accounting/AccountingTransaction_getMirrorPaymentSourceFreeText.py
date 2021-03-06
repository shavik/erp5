if selection_name is None:
  # TODO: this should definitivly be REQUEST chached
  selection_name = 'accounting_selection'

section_category=context.portal_selections.getSelectionParamsFor(selection_name).get('section_category')
if not section_category:
  return

if brain is not None:
  transaction = brain.getObject()
else:
  transaction = context

source_section = transaction.getSourceSectionValue()
if source_section is not None and source_section.isMemberOf(section_category):
  mirror_payment = transaction.getDestinationPaymentValue()
else:
  mirror_payment = transaction.getSourcePaymentValue()

if mirror_payment is None:
  return None
return mirror_payment.getSourceFreeText()
