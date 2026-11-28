import { Dropdown, DropdownButton, Form } from "react-bootstrap";

export interface Choice {
  id: number | string;
  name: string;
  extraText?: string;
}

interface DropdownProps<T extends Choice> {
  choices: T[];
  onChoiceSelected: (choice_id: T | null) => void;
  selectedChoice?: T;
  noSelectionText?: string;
}

const TapirDropdown = <T extends Choice>({
  choices,
  onChoiceSelected,
  selectedChoice,
  noSelectionText = "Select an option",
}: DropdownProps<T>) => {
  return (
    <DropdownButton
      title={selectedChoice ? selectedChoice.name : noSelectionText}
      variant={selectedChoice ? "primary" : "outline-primary"}
      onSelect={(selected_index) => {
        onChoiceSelected(
          selected_index ? choices[parseInt(selected_index)] : null,
        );
      }}
    >
      {choices.map((choice, index) => (
        <Dropdown.Item
          key={index}
          eventKey={index}
          style={{ maxWidth: "500px" }}
        >
          {choice.name}
          {choice.extraText && (
            <>
              <br />
              <Form.Text style={{ textWrap: "wrap" }}>
                {choice.extraText}
              </Form.Text>
            </>
          )}
        </Dropdown.Item>
      ))}
    </DropdownButton>
  );
};

export default TapirDropdown;
